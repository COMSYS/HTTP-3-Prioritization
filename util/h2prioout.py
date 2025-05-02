import json
import logging

from testbed.setup.retrieveh2prio import retrieveh2prio
from testbed.util.utils import LoggingHelper


def h2prioout(
    loghelp: LoggingHelper,
    namespace,
    workdir="",
    website="",
    h2prioout="",
    n="",
):
    loghandler = logging.FileHandler(h2prioout + ".log")
    loghelp.addHandler(loghandler)
    out = []
    n = 30
    if n:
        n = int(n)
    for i in range(n):
        chromelog, chromeerrorlog, chromeperf = retrieveh2prio(
            namespace, workdir, website
        )
        firefoxlog, firefoxerrorlog, _ = retrieveh2prio(
            namespace, workdir, website, firefox=True
        )

        out.append(
            {
                "firefoxlog": firefoxlog,
                "chromelog": chromelog,
                "chromeperf": chromeperf,
                "chromeerrorlog": chromeerrorlog,
                "firefoxerrorlog": firefoxerrorlog,
            }
        )

    with open(h2prioout, "w") as f:
        json.dump(out, f)
