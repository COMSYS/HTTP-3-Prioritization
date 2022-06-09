from setup.process import run
from setup.utils import rand_str
import os

def start_dnsmasq(dns_entries, namespace, nsid):

    path = os.path.abspath("temporary/dnsmasq/%s" % nsid)

    os.makedirs(path)

    hosts_filename = path + "/hosts"
    config_filename = path + "/conf"
    pid_filename = path + "/dnsmasq.pid"

    hosts = "\n".join([ip + " " + hostname for ip, hostname in dns_entries]) + "\n"

    config = ""

    with open(hosts_filename,"w") as f:
        f.write(hosts)

    with open(config_filename,"w") as f:
        f.write(config)
    
    args = ["dnsmasq", "--no-resolv", "--no-hosts", "-C", config_filename, "-H", hosts_filename, "-x", pid_filename]
    p = run(args, namespace)
    return p
