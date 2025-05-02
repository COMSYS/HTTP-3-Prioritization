import json
import logging
import math
from glob import glob
from pathlib import Path

from learning import LEARNING_BASE_DIR
from testbed import BASE_DIR, BROWSERTIME_DIR, LIGHTHOUSE_DIR
from testbed.setup import dnsmasq, h2o
from testbed.setup.process import run
from testbed.util import http_record_pb2

logger = logging.getLogger("setup")
logger.setLevel(logging.ERROR)
logger.propagate = False
handler = logging.FileHandler(LEARNING_BASE_DIR / "run_data" / "current_run.log")
formatter = logging.Formatter("[%(asctime)s-%(name)s-%(levelname)s]: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def runcmd(cmd):
    try:
        args = cmd.split(" ")
        run(args)
    except Exception as e:
        logger.error(f"Error running command: {e}")


def add_dummy_interface(name, ip, namespace):
    try:
        run(["ip", "link", "add", name, "type", "dummy"], namespace)
        run(["ip", "link", "set", "dev", name, "up"], namespace)
        run(["ip", "addr", "add", "%s/32" % ip, "dev", name], namespace)
    except Exception as e:
        logger.error(f"Error adding dummy interface: {e}")


def cleanup(nsid, lighthouse=True):
    try:
        cleanup_processes(nsid, lighthouse=lighthouse)
        cleanup_files(nsid)
    except Exception as e:
        logger.error(f"Error cleaning up: {e}")


def cleanup_files(nsid):
    try:
        path = BASE_DIR / f"temporary/h2o/{nsid}"
        gopath = BASE_DIR / f"temporary/go/{nsid}"
        dnsmasqpath = BASE_DIR / f"temporary/dnsmasq/{nsid}"

        run(["rm", "-rf", path], exceptionok=True)
        run(["rm", "-rf", gopath], exceptionok=True)
        run(["rm", "-rf", dnsmasqpath], exceptionok=True)
    except Exception as e:
        logger.error(f"Error cleaning up files: {e}")


def cleanup_processes(nsid, lighthouse=True):
    try:
        path = BASE_DIR / f"temporary/h2o/{nsid}"
        files = glob(str(path / "*/h2o.pid"))

        gopath = BASE_DIR / f"temporary/go/{nsid}"
        files.append(str(gopath / "fcgi.pid"))

        dnsmasqpath = BASE_DIR / f"temporary/dnsmasq/{nsid}"
        files.append(str(dnsmasqpath / "dnsmasq.pid"))

        pids = []

        for filename in files:
            path = Path(filename)
            if path.exists() and path.is_file():
                try:
                    with path.open() as f:
                        pids.append(f.read().strip())
                except (IOError, OSError, PermissionError) as e:
                    logger.warning(f"Could not read file {filename}: {e}")
                    pass

        for pid in pids:
            run(["kill", "-9", pid], exceptionok=True)

        if lighthouse:
            run([f"{LIGHTHOUSE_DIR}/stop.sh", nsid], exceptionok=True)
        else:
            run([f"{BROWSERTIME_DIR}/docker/stop_docker.sh", nsid], exceptionok=True)

        run(["rm", "/var/run/netns/%s-docker" % nsid], exceptionok=True)

        run(["ip", "netns", "delete", "%s-servers" % nsid], exceptionok=True)
        run(["ip", "netns", "delete", "%s-ns0" % nsid], exceptionok=True)
        run(["ip", "netns", "delete", "%s-ns1" % nsid], exceptionok=True)
        run(["ip", "netns", "delete", "%s-ns2" % nsid], exceptionok=True)
        run(["ip", "netns", "delete", "%s-ns3" % nsid], exceptionok=True)
        run(["ip", "netns", "delete", "%s-client" % nsid], exceptionok=True)

        run(["ip", "link", "del", "veth%s0" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s1" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s2" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s3" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s4" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s5" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s6" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s7" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s8" % nsid], exceptionok=True)
        run(["ip", "link", "del", "veth%s9" % nsid], exceptionok=True)
    except Exception as e:
        logger.error(f"Error cleaning up processes: {e}")


def setup_docker(nsid, lighthouse=True):
    try:
        if lighthouse:
            run([f"{LIGHTHOUSE_DIR}/start.sh", nsid])
        else:
            run([f"{BROWSERTIME_DIR}/docker/start_docker.sh", nsid])
    except Exception as e:
        logger.error(f"Error setting up docker: {e}")


def setup(
    nsid,
    directory,
    rewrite_file=None,
    allsameip=False,
    only_h2=False,
    prioritization=None,
    cc="reno",
    lighthouse=True,
):
    try:
        cleanup(nsid, lighthouse=lighthouse)
        setup_docker(nsid, lighthouse=lighthouse)
        setup_namespaces(nsid)
        return setup_servers(
            nsid,
            directory,
            rewrite_file,
            allsameip,
            only_h2,
            prioritization=prioritization,
            cc=cc,
        )
    except Exception as e:
        logger.error(f"Error setting up: {e}")


def setup_namespaces(nsid):
    try:
        run(["ip", "netns", "add", "%s-servers" % nsid])
        run(["ip", "link", "set", "dev", "lo", "up"], "%s-servers" % nsid)

        for i in range(4):
            runcmd("ip netns add %s-ns%d" % (nsid, i))
            runcmd(
                "ip netns exec %s-ns%d ip link add br%s%d type bridge"
                % (nsid, i, nsid, i)
            )
            runcmd(
                "ip netns exec %s-ns%d ip link set dev br%s%d up" % (nsid, i, nsid, i)
            )

        for i in range(0, 10, 2):
            runcmd(
                "ip link add veth%s%d type veth peer name veth%s%d"
                % (nsid, i, nsid, i + 1)
            )
            runcmd("ethtool -K veth%s%d tso off gso off gro off" % (nsid, i))
            runcmd("ethtool -K veth%s%d tso off gso off gro off" % (nsid, i + 1))

        # ns-servers - veth0  | veth1 - ns0 - veth2 | veth3 - ns1 - veth4 | veth5 - ns2 - veth6 | veth7 - ns3 - veth8 | veth9 - ns-client <> docker
        #                                      tbf                  netem   netem                  tbf

        for i in range(10):
            m = [-1, 0, 0, 1, 1, 2, 2, 3, 3, -1]
            if m[i] != -1:
                runcmd("ip link set veth%s%d netns %s-ns%d" % (nsid, i, nsid, m[i]))
                runcmd(
                    "ip netns exec %s-ns%d ip link set veth%s%d master br%s%d"
                    % (nsid, m[i], nsid, i, nsid, m[i])
                )
                runcmd(
                    "ip netns exec %s-ns%d ip link set dev veth%s%d up"
                    % (nsid, m[i], nsid, i)
                )

        runcmd("ip netns add %s-client" % nsid)
        run(["ip", "link", "set", "dev", "lo", "up"], "%s-client" % nsid)

        runcmd("ip link set veth%s0 netns %s-servers" % (nsid, nsid))
        runcmd("ip netns exec %s-servers ip link set dev veth%s0 up" % (nsid, nsid))
        runcmd(
            "ip netns exec %s-servers ip addr add 10.0.1.1/24 dev veth%s0"
            % (nsid, nsid)
        )

        runcmd("ip link add vethd%s1 type veth peer name vethd%s2" % (nsid, nsid))
        runcmd("ethtool -K vethd%s1 tso off gso off gro off" % nsid)
        runcmd("ethtool -K vethd%s2 tso off gso off gro off" % nsid)

        runcmd("ip link add vethd%s3 type veth peer name vethd%s4" % (nsid, nsid))
        runcmd("ethtool -K vethd%s3 tso off gso off gro off" % nsid)
        runcmd("ethtool -K vethd%s4 tso off gso off gro off" % nsid)

        runcmd("ip link set vethd%s2 netns %s-docker" % (nsid, nsid))
        runcmd("ip netns exec %s-docker ip link set dev vethd%s2 up" % (nsid, nsid))
        runcmd(
            "ip netns exec %s-docker ip addr add 10.0.1.3/24 dev vethd%s2"
            % (nsid, nsid)
        )
        runcmd("ip netns exec %s-docker ip route add default via 10.0.1.1" % nsid)

        runcmd("ip link set vethd%s1 netns %s-client" % (nsid, nsid))
        runcmd("ip netns exec %s-client ip link set dev vethd%s1 up" % (nsid, nsid))

        runcmd("ip link set vethd%s3 netns %s-client" % (nsid, nsid))
        runcmd("ip netns exec %s-client ip link set dev vethd%s3 up" % (nsid, nsid))
        runcmd("ip link set vethd%s4 netns %s-client" % (nsid, nsid))
        runcmd("ip netns exec %s-client ip link set dev vethd%s4 up" % (nsid, nsid))
        runcmd(
            "ip netns exec %s-client ip addr add 10.0.1.4/24 dev vethd%s4"
            % (nsid, nsid)
        )

        runcmd("ip link set veth%s9 netns %s-client" % (nsid, nsid))
        runcmd("ip netns exec %s-client ip link set dev veth%s9 up" % (nsid, nsid))

        runcmd("ip netns exec %s-client ip link add brd%s0 type bridge" % (nsid, nsid))
        runcmd("ip netns exec %s-client ip link set dev brd%s0 up" % (nsid, nsid))
        runcmd(
            "ip netns exec %s-client ip link set vethd%s1 master brd%s0"
            % (nsid, nsid, nsid)
        )
        runcmd(
            "ip netns exec %s-client ip link set veth%s9 master brd%s0"
            % (nsid, nsid, nsid)
        )
        runcmd(
            "ip netns exec %s-client ip link set vethd%s3 master brd%s0"
            % (nsid, nsid, nsid)
        )
        runcmd(
            "ip netns exec %s-client sysctl -w net.ipv4.ip_unprivileged_port_start=1"
            % nsid
        )

        #   runcmd("ip netns exec %s-client sysctl -w net.ipv4.ip_forward=1" % nsid)
        runcmd("ip netns exec %s-servers sysctl -w net.ipv4.ip_forward=1" % nsid)
        runcmd("ip netns exec %s-servers sysctl -w net.ipv4.ip_forward=1" % nsid)
        runcmd(
            "ip netns exec %s-servers sysctl -w net.ipv4.ip_unprivileged_port_start=1"
            % nsid
        )

        set_bottleneck(nsid, bw=1, rtt=200, bdp=10, first=True)
    except Exception as e:
        logger.error(f"Error setting up namespaces: {e}")


def setup_servers(
    nsid,
    directory,
    rewrite_file=None,
    allsameip=False,
    only_h2=False,
    prioritization=None,
    cc="reno",
):
    try:
        directory = Path(directory)
        files = glob(str(directory / "*.save"))

        fcgipath = BASE_DIR / f"temporary/go/{nsid}"
        fcgipath.mkdir(parents=True, exist_ok=True)
        fcgisocket = fcgipath / "fcgi.sock"
        fcgipidfile = fcgipath / "fcgi.pid"
        fastcgi = run(
            [f"{BASE_DIR}/go_fastcgi/start.sh", directory, fcgisocket, fcgipidfile],
            bg=True,
        )

        unique_ip = set()
        hostnames_to_ip = {}

        if allsameip:
            logger.info("Use same ip for all websites")
        elif rewrite_file is not None:
            with open(rewrite_file) as f:
                rewrites = json.load(f)
            for rewrite in rewrites:
                ip = rewrite["ip"]
                for host in rewrite["hosts"]:
                    hostnames_to_ip[host] = ip

        unique_ip_and_port_to_hosts = {}

        for filename in files:
            protobuf = http_record_pb2.RequestResponse()

            with open(filename, "rb") as f:
                protobuf.ParseFromString(f.read())

            ip = protobuf.ip
            port = protobuf.port
            request_headers = {}
            for request_header in protobuf.request.header:
                k = request_header.key.decode()
                v = request_header.value.decode()
                k_stripped = k.lower().strip()
                request_headers[k_stripped] = v

            hostname = request_headers["host"]
            if allsameip:
                ip = "9.9.9.9"
                hostnames_to_ip[hostname] = ip
            else:
                if hostname in hostnames_to_ip:
                    ip = hostnames_to_ip[hostname]
                else:
                    hostnames_to_ip[hostname] = ip

            unique_ip.add(ip)

            if not (ip, port) in unique_ip_and_port_to_hosts:
                unique_ip_and_port_to_hosts[(ip, port)] = []
            unique_ip_and_port_to_hosts[(ip, port)].append(hostname)

        for counter, ip in enumerate(unique_ip):
            add_dummy_interface("sharded%d" % counter, ip, "%s-servers" % nsid)

        servers = []
        for (ip, port), hostnames in unique_ip_and_port_to_hosts.items():
            if not only_h2 and port == 80:
                logging.info("port 80 and quic selected?!")
            server = h2o.start_h2o(
                ip,
                port,
                hostnames,
                "%s-servers" % nsid,
                nsid,
                fcgisocket,
                only_h2=only_h2,
                prioritization=prioritization,
                cc=cc,
            )
            servers.append(server)

        # DNS stuff

        dns_entries = []
        for hostname, ip in hostnames_to_ip.items():
            dns_entries.append((ip, hostname))

        dnsmasq.start_dnsmasq(dns_entries, "%s-client" % nsid, nsid)

        logger.info("setup done, namespace servers setup")
        return [fastcgi] + servers
    except Exception as e:
        logger.error(f"Error setting up servers: {e}")


def set_bottleneck(nsid, bw, rtt, bdp, first=False, bwup=None, loss=0):
    try:
        mtu = 1514

        if not first:
            op = "change"
        else:
            op = "add"

        if bwup is None:
            bwup = bw

        bdp_bytes = int(math.ceil((bw / 8.0 * 1024.0 * 1024.0) * (rtt / 1000.0) * bdp))
        oversized_bdp_packets = int(math.ceil(bdp_bytes * 10.0 / mtu))

        if loss == 0.0:
            # adding qdiscs - delay
            runcmd(
                "ip netns exec %s-ns1 tc qdisc %s dev veth%s4 root handle 1: netem delay %fms limit %d"
                % (nsid, op, nsid, rtt / 2, oversized_bdp_packets)
            )
            runcmd(
                "ip netns exec %s-ns2 tc qdisc %s dev veth%s5 root handle 1: netem delay %fms limit %d"
                % (nsid, op, nsid, rtt / 2, oversized_bdp_packets)
            )
        else:
            if type(loss) == str:
                # adding qdiscs - delay (burst) loss
                runcmd(
                    "ip netns exec %s-ns1 tc qdisc %s dev veth%s4 root handle 1: netem delay %fms loss %s limit %d"
                    % (nsid, op, nsid, rtt / 2, loss, oversized_bdp_packets)
                )
                runcmd(
                    "ip netns exec %s-ns2 tc qdisc %s dev veth%s5 root handle 1: netem delay %fms loss %s limit %d"
                    % (nsid, op, nsid, rtt / 2, loss, oversized_bdp_packets)
                )
            else:
                # adding qdiscs - delay loss
                runcmd(
                    "ip netns exec %s-ns1 tc qdisc %s dev veth%s4 root handle 1: netem delay %fms loss random %f%% limit %d"
                    % (nsid, op, nsid, rtt / 2, loss * 100.0, oversized_bdp_packets)
                )
                runcmd(
                    "ip netns exec %s-ns2 tc qdisc %s dev veth%s5 root handle 1: netem delay %fms loss random %f%% limit %d"
                    % (nsid, op, nsid, rtt / 2, loss * 100.0, oversized_bdp_packets)
                )

        # adding qdiscs - rate shaping
        runcmd(
            "ip netns exec %s-ns0 tc qdisc %s dev veth%s2 root handle 1: tbf rate %fmbit burst %d limit %d"
            % (nsid, op, nsid, bw, mtu, bdp_bytes)
        )
        runcmd(
            "ip netns exec %s-ns3 tc qdisc %s dev veth%s7 root handle 1: tbf rate %fmbit burst %d limit %d"
            % (nsid, op, nsid, bwup, mtu, bdp_bytes)
        )

        logger.info("set %f %d %f" % (bw, rtt, bdp))
    except Exception as e:
        logger.error(f"Error setting bottleneck: {e}")
