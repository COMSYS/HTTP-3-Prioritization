import logging
import traceback
from time import sleep

from setup.setup import cleanup, set_bottleneck, setup

from testbed.util.docker import Docker


def retrieveh2prio(namespace, workdir, website, firefox=False):
    try:
        chromeperf_content = None
        logfile_content = None
        servers = []

        servers = setup(namespace, workdir, None, True, only_h2=True)
        set_bottleneck(namespace, bw=10, rtt=100, bdp=1)

        selected_server = None
        for server in servers:
            additional = server.get_additionalargs()
            if additional:
                hostnames = additional["hostnames"]
                if website in hostnames:
                    selected_server = server
                    break

        assert selected_server is not None, "domain not found in started servers"

        bt = Docker(namespace, website, only_h2=True, firefox=firefox)
        bt.start()
        if firefox:
            logging.info("browsertime (firefox) started")
        else:
            logging.info("browsertime (chromium) started")
        while bt.is_running():
            sleep(1)
        if not firefox:
            chromeperf_content = bt.get("chromeCDPlog-1.json.gz")
        logfile_content = selected_server.get("access.log")
        errlogfile_content = selected_server.get("error.log")

    except BaseException as e:
        for op in servers:
            op.willbekilled()
        logging.info("main received %s" % repr(e))
        traceback.print_exc()
    finally:
        for op in servers:
            op.willbekilled()
        cleanup(namespace)

    if logfile_content:
        return (logfile_content, errlogfile_content, chromeperf_content)

    return (None, None, None)
