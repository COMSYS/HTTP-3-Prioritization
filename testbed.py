import json
import logging
import time
from pathlib import Path
from time import sleep

from testbed.setup.setup import (
    cleanup,
    set_bottleneck,
    setup_docker,
    setup_docker,
    setup_namespaces,
    setup_servers,
)
from testbed.util.docker import Docker


class Testbed:
    """Encapsulates testbed functionality."""

    def __init__(
        self,
        evalconfig: dict,
        namespace: str,
        run_dir: Path,
        run_logger: logging.Logger,
    ):
        self.evalconfig = evalconfig
        self.namespace = namespace
        self.run_dir = run_dir
        if not self.run_dir.is_dir():
            self.run_dir.mkdir(parents=True, exist_ok=False, mode=0o777)
        self.servers = []
        self.browsertime = None
        self.logger = run_logger.getChild("testbed")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        handler = logging.FileHandler(self.run_dir / "testbed.log")
        handler.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "[%(asctime)s-%(name)s-%(levelname)s]: %(message)s"
        )
        handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)
        self.logger.addHandler(handler)
        self.logger.info("Testbed initialized")
        with open(self.run_dir / "config.json", "w") as f:
            json.dump(self.evalconfig, f, indent=4)

    def setup(self, lighthouse=True):
        """First clean up then set up namespaces and servers according to namespace name."""
        try:
            cleanup(self.namespace)
            start = time.time()
            setup_docker(self.namespace, lighthouse=lighthouse)
            end = time.time()
            self.logger.info(f"setup_browsertime took {end - start} seconds")
            start = time.time()
            setup_namespaces(self.namespace)
            end = time.time()
            self.logger.info(f"setup_namespaces took {end - start} seconds")
            start = time.time()
            self.logger.info(
                f"Setting up server with mode {self.evalconfig['priomode']} and file {self.evalconfig['priorities']}"
            )
            self.servers = setup_servers(
                self.namespace,
                self.evalconfig["resources"],
                None,
                True,
                prioritization={
                    "mode": self.evalconfig["priomode"],
                    "file": self.evalconfig["priorities"],
                },
                cc=self.evalconfig["cc"],
            )
            end = time.time()
            self.logger.info(f"setup_servers took {end - start} seconds")
            if not "bwup" in self.evalconfig:
                self.evalconfig["bwup"] = self.evalconfig["bwdown"]
            start = time.time()
            set_bottleneck(
                self.namespace,
                self.evalconfig["bwdown"],
                self.evalconfig["rtt"],
                self.evalconfig["bdp"],
                bwup=self.evalconfig["bwup"],
                loss=self.evalconfig["loss"],
            )
            end = time.time()
            self.logger.info(f"set_bottleneck took {end - start} seconds")
            timeout = 300
            if self.evalconfig["bwdown"] < 2:
                timeout = 900
            self.docker = Docker(
                self.namespace,
                self.evalconfig["website"],
                timeout=timeout,
                lighthouse=lighthouse,
            )
        except Exception as e:
            for op in self.servers:
                op.willbekilled()
            self.logger.exception(f"Error setting up testbed: {e}")

    def cleanup(self, lighthouse=True):
        """Clean up the testbed."""
        try:
            for op in self.servers:
                op.willbekilled()
            cleanup(self.namespace, lighthouse=lighthouse)
        except Exception as e:
            self.logger.error(f"Error cleaning up testbed: {e}")

    def run_browsertime(self, output_dir: Path):
        """Run browsertime and copy over the results."""
        try:
            start = time.time()
            self.docker.start()
            self.logger.info("browsertime (chrome) started")
            while self.docker.is_running():
                sleep(0.1)

            self.docker.copy_over(str(output_dir / "browsertime"))
            for i, server in enumerate(self.servers):
                server.copy_over(str(output_dir / f"server{i}"))

            self.docker.parse("browsertime.json")
            har = self.docker.parse("browsertime.har")

            versions = [
                entry["request"]["httpVersion"] for entry in har["log"]["entries"]
            ]
            assert set(versions) == {"h3"}, set(versions)
            end = time.time()
            self.logger.info(f"browsertime took {end - start} seconds")
        except Exception as e:
            self.logger.error(f"Error running browsertime: {e}")

    def run_lighthouse(self, output_dir: Path):
        """Run lighthouse and copy over the results."""
        try:
            start = time.time()
            self.docker.start()
            self.logger.info("lighthouse (chrome) started")
            while self.docker.is_running():
                sleep(0.1)

            self.docker.copy_over(str(output_dir / "lighthouse"))
            for i, server in enumerate(self.servers):
                server.copy_over(str(output_dir / f"server{i}"))

            # self.docker.parse("lighthouse-report.json")
            end = time.time()
            self.logger.info(f"lighthouse took {end - start} seconds")
        except Exception as e:
            self.logger.error(f"Error running lighthouse: {e}")
