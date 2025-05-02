import json
from glob import glob
from multiprocessing import Pool
from pathlib import Path

from testbed.util.hol import hol_compute

CPUS = 1


def get_results(rep_dir: Path, run: int):

    with open(f"{rep_dir.parent.parent}/config.json") as f:
        config = json.load(f)

    copymetrics = [
        ("FirstVisualChange", "fvc"),
        ("LastVisualChange", "lvc"),
        ("SpeedIndex", "si"),
        ("VisualComplete85", "vc85"),
        ("VisualComplete95", "vc95"),
        ("VisualComplete99", "vc99"),
    ]

    try:
        hol_blocked = hol_compute(f"{rep_dir}/browsertime/chromeNetlog-1.json.gz")
        config["hol_blocked"] = hol_blocked["stream_hol"]

        with open(f"{rep_dir}/browsertime/browsertime.json") as f:
            browsertime = json.load(f)

        visualmetrics = browsertime[0]["visualMetrics"][0]
        for fromfield, tofield in copymetrics:
            config[tofield] = visualmetrics[fromfield]

        config["plt"] = browsertime[0]["statistics"]["timings"]["pageTimings"][
            "pageLoadTime"
        ]["median"]
        config["runtime"] = browsertime[0]["timestamps"][0]
        config["conf_dir"] = rep_dir
        config["burst"] = 0
        if config["loss"] == "gemodel 0.4081632% 20%":
            config["burst"] = 5
            config["loss"] = 0.02
        if config["loss"] == "gemodel 0.2040816% 10%":
            config["burst"] = 10
            config["loss"] = 0.02
        if config["loss"] == "gemodel 0.1360544% 6.66667%":
            config["burst"] = 15
            config["loss"] = 0.02
        return config
    except Exception as e:
        print("issue", run, config, e)
        return None
