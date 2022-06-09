import sys
from glob import glob
import json
import socket
from hol import hol_compute
from multiprocessing import Pool

CPUS = 1

def do(x):
    conf_dir, run, date, host = x

    with open("%s/config.json" % conf_dir) as f:
        config = json.load(f)

    config["machine"] = host
    #print(config)

    copymetrics = [("FirstVisualChange", "fvc"), ("LastVisualChange", "lvc"), ("SpeedIndex", "si"), ("VisualComplete85", "vc85"), ("VisualComplete95", "vc95"), ("VisualComplete99", "vc99")]

    try:
        hol_blocked = hol_compute("%s/browsertime/chromeNetlog-1.json.gz" % conf_dir)
        config["hol_blocked"] = hol_blocked["stream_hol"]

        with open("%s/browsertime/browsertime.json" % conf_dir) as f:
            browsertime = json.load(f)

        visualmetrics = browsertime[0]["visualMetrics"][0]
        for fromfield, tofield in copymetrics:
            config[tofield] = visualmetrics[fromfield]

        config["plt"] = browsertime[0]["statistics"]["timings"]["pageTimings"]["pageLoadTime"]["median"]
        config["runtime"] = browsertime[0]["timestamps"][0]
        config["conf_dir"] = conf_dir
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

p = Pool(CPUS)
data = []
for dir in glob("%s/*/*/*" % sys.argv[1]):
  dirparts = dir.split("/")
  repeat = dirparts[-1]
  date = dirparts[-2]
  host = int(dirparts[-3])
  run = int(repeat.split("repeat-")[1])
  data += p.imap_unordered(do, [(x, run, date, host) for x in glob("%s/*" % dir)])

with open("out.jsonl","w") as f:
    for d in data:
        if d is not None:
            json.dump(d, f)
            f.write("\n")
