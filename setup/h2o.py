from setup.process import run
import os
import hashlib
import logging

def start_h2o(addr, port, hostnames, namespace, nsid, fcgisocket, only_h2=False, prioritization=None, cc="reno"):
    gdb = False

    hostnames = sorted(list(set(hostnames)))
    hostnames_string = ",".join(hostnames)

    m = hashlib.md5()
    m.update(hostnames_string.encode())
    idx = m.hexdigest()
    logging.info("md5 %s %s" % (idx, hostnames_string))

    path = os.path.abspath("temporary/h2o/%s/%s-%d" % (nsid, idx, port))

    os.makedirs(path)

    pid_filename = path + "/h2o.pid"
    log_filename = path + "/access.log"
    errorlog_filename = path + "/error.log"
    config_filename = path + "/h2o.cfg"


    cert_path = os.path.abspath("temporary/certificates/%s" % idx)
    key_filename = cert_path + "/cert.key"
    cert_filename = cert_path + "/cert.crt"

    if not os.path.exists(cert_path):
        logging.info("generate certificates for %s" % hostnames_string)
        os.makedirs(cert_path)
        cert_basename = cert_path + "/cert"

        cert_args = ["./setup/certificates/cert.sh", cert_basename]
        cert_args += hostnames

        run(cert_args)

    config_file = "" +\
        "pid-file: " + pid_filename + "\n" +\
        "num-threads: 4\n"  +\
        "error-log: " + errorlog_filename + "\n"

    config_file += "" +\
        "hosts:\n" +\
        "  \"*\":\n"

    if port != 80:
        config_file += "" +\
            "    listen: &ssl_listen\n" +\
            "      host: " + addr + "\n" +\
            "      port: " + str(port) + "\n" +\
            "      ssl:\n" +\
            "        key-file: " + key_filename + "\n" +\
            "        certificate-file: " + cert_filename + "\n" +\
            "        ocsp-update-interval: 0\n"
        if not only_h2:
            config_file += \
            "      type: quic\n"
        config_file += "" +\
            "      cc: " + cc + "\n"

    else:
        config_file += "" +\
            "    listen:\n" +\
            "      host: " + addr + "\n" +\
            "      port: " + str(port) + "\n"

    config_file += "" +\
        "    paths:\n" +\
        "      \"/\":\n" +\
        "        access-log:\n" +\
        "          path: " + log_filename + "\n" +\
        "          format: \"%h %l %u %t \\\"%r\\\" %s %b \\\"%{Referer}i\\\" \\\"%{User-agent}i\\\" %{http2.priority.received.weight}x %{http2.priority.received.parent}x %V\"\n" +\
        "        fastcgi.connect:\n" +\
        "          port: " + fcgisocket + "\n" +\
        "          type: unix\n"
    
    with open(config_filename, "w") as f:
        f.write(config_file)
    
    run(["touch", pid_filename])
    run(["chmod", "777", pid_filename])

    add_args = []
    
    if prioritization:
        assert "file" in prioritization
        assert "mode" in prioritization
        add_args  += ["-p", prioritization["mode"], "-P", prioritization["file"]]

    args = ["bash", "-c", "h2o " + " ".join(add_args) + " -c " + config_filename]
    
    p = run(args, namespace, cwd=path, bg=True, additionalargs={"path":path, "hostnames":hostnames})
    return p
