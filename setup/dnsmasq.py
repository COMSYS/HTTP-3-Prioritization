from testbed import BASE_DIR
from testbed.setup.process import run


def start_dnsmasq(dns_entries, namespace, nsid):

    dnsmasq_path = BASE_DIR / f"temporary/dnsmasq/{nsid}"
    dnsmasq_path.mkdir(parents=True, exist_ok=True)

    hosts_filename = dnsmasq_path / "hosts"
    config_filename = dnsmasq_path / "conf"
    pid_filename = dnsmasq_path / "dnsmasq.pid"

    hosts = "\n".join([ip + " " + hostname for ip, hostname in dns_entries]) + "\n"

    config = ""

    with open(hosts_filename, "w") as f:
        f.write(hosts)

    with open(config_filename, "w") as f:
        f.write(config)

    args = [
        "dnsmasq",
        "--no-resolv",
        "--no-hosts",
        "-C",
        str(config_filename),
        "-H",
        str(hosts_filename),
        "-x",
        str(pid_filename),
    ]
    p = run(args, namespace)
    return p
