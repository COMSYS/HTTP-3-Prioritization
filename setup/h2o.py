import hashlib
import logging
import os

from learning import LEARNING_BASE_DIR
from testbed import BASE_DIR
from testbed.setup.process import run

logger = logging.getLogger("h20")
logger.setLevel(logging.INFO)
logger.propagate = False
handler = logging.FileHandler(
    LEARNING_BASE_DIR / "run_data" / "current_run_process.log"
)
formatter = logging.Formatter("[%(asctime)s-%(name)s-%(levelname)s]: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def start_h2o(
    addr,
    port,
    hostnames,
    namespace,
    nsid,
    fcgisocket,
    only_h2=False,
    prioritization=None,
    cc="reno",
):
    try:
        hostnames = sorted(list(set(hostnames)))
        hostnames_string = ",".join(hostnames)

        m = hashlib.md5()
        m.update(hostnames_string.encode())
        idx = m.hexdigest()
        logging.info("md5 %s %s" % (idx, hostnames_string))

        h2o_path = BASE_DIR / f"temporary/h2o/{nsid}/{idx}-{port}"
        h2o_path.mkdir(parents=True, exist_ok=True)

        pid_filename = h2o_path / "h2o.pid"
        log_filename = h2o_path / "access.log"
        errorlog_filename = h2o_path / "error.log"
        config_filename = h2o_path / "h2o.cfg"

        cert_path = BASE_DIR / f"temporary/certificates/{idx}"
        key_filename = cert_path / "cert.key"
        cert_filename = cert_path / "cert.crt"

        if not os.path.exists(cert_path):
            logging.info(f"generate certificates for {hostnames_string}")
            os.makedirs(cert_path)
            cert_basename = cert_path / "cert"

            cert_args = [f"{BASE_DIR}/setup/certificates/cert.sh", str(cert_basename)]
            cert_args += hostnames

            run(cert_args)

        config_file = (
            ""
            + "pid-file: "
            + str(pid_filename)
            + "\n"
            + "num-threads: 4\n"
            + "error-log: "
            + str(errorlog_filename)
            + "\n"
        )

        config_file += "" + "hosts:\n" + '  "*":\n'

        if port != 80:
            config_file += (
                ""
                + "    listen: &ssl_listen\n"
                + "      host: "
                + addr
                + "\n"
                + "      port: "
                + str(port)
                + "\n"
                + "      ssl:\n"
                + "        key-file: "
                + str(key_filename)
                + "\n"
                + "        certificate-file: "
                + str(cert_filename)
                + "\n"
                + "        ocsp-update-interval: 0\n"
            )
            if not only_h2:
                config_file += "      type: quic\n"
            config_file += "" + "      cc: " + cc + "\n"

        else:
            config_file += (
                ""
                + "    listen:\n"
                + "      host: "
                + addr
                + "\n"
                + "      port: "
                + str(port)
                + "\n"
            )

        config_file += (
            ""
            + "    paths:\n"
            + '      "/":\n'
            + "        access-log:\n"
            + "          path: "
            + str(log_filename)
            + "\n"
            + '          format: "%h %l %u %t \\"%r\\" %s %b \\"%{Referer}i\\" \\"%{User-agent}i\\" %{http2.priority.received.weight}x %{http2.priority.received.parent}x %V"\n'
            + "        fastcgi.connect:\n"
            + "          port: "
            + str(fcgisocket)
            + "\n"
            + "          type: unix\n"
        )

        with open(config_filename, "w") as f:
            f.write(config_file)

        run(["touch", pid_filename])
        run(["chmod", "777", pid_filename])

        add_args = []

        if prioritization:
            assert "file" in prioritization
            assert "mode" in prioritization
            add_args += ["-p", prioritization["mode"], "-P", prioritization["file"]]

        args = [
            "bash",
            "-c",
            "h2o " + " ".join(add_args) + " -c " + str(config_filename),
        ]

        p = run(
            args,
            namespace,
            cwd=h2o_path,
            bg=True,
            additionalargs={"path": h2o_path, "hostnames": hostnames},
        )
        return p
    except Exception as e:
        logger.exception(f"Error starting h2o: {e}")
