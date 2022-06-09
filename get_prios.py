from mahimahi import mm_files
import json 
import sys
from h2prio.resource_tools import get_resource_types, classify_chrome_prio, classify_firefox_prio, get_resource_streams
import argparse
parser = argparse.ArgumentParser()

parser.add_argument('--workdir')
parser.add_argument('--input')
parser.add_argument('--output')

args = parser.parse_args()

assert args.workdir is not None
assert args.input is not None
assert args.output is not None

workdir = args.workdir #mahimahi workdir
output = args.output # output file
input = args.input # input json from main.py

available_pages = mm_files.preload_files(workdir)
priorities = json.load(open(input))

available_urls = [page["request_host"] + page["request_uri"] for page in available_pages]
available_fit = {}

def get_diff(a,b):
    out = []
    for key in set(a.keys()) | set(b.keys()):
        if key not in a:
            out.append({"key":key, "b":b[key]})
        elif key not in b:
            out.append({"key":key, "a":a[key]})
        elif a[key] != b[key]:
            out.append({"key":key, "a":a[key],"b":b[key]})
    return out

for uri in available_urls:
    keyuri = uri.split('?',1)[0]
    if not keyuri in available_fit:
        available_fit[keyuri] = []
    available_fit[keyuri].append(uri)

def best_fit(a, al):
    best_fit_item = None
    best_fit = -1
    for item in al:
        fit = mm_files.calc_fit(a, item)
        if fit > best_fit:
            best_fit_item = item
            best_fit = fit
    return best_fit_item

ff_classes = []
chrome_classes = []
types = []

#boil urls down to mahimahi urls
for priority in priorities:
    if priority["firefoxlog"] is None:
        print("firefox missing, skip", file=sys.stderr)
        continue
    if priority["chromelog"] is None:
        print("chrome missing, skip", file=sys.stderr)
        continue
    if priority["chromeperf"] is None:
        print("chromeperf missing, skip", file=sys.stderr)
        continue
    firefox_streams = get_resource_streams(priority["firefoxlog"])
    chrome_streams = get_resource_streams(priority["chromelog"])
    chrome_types = get_resource_types(priority["chromeperf"])
    chrome = {}
    for stream in chrome_streams:
        uri = stream["url"]
        keyuri = uri.split('?',1)[0]
        if keyuri in available_fit:
            newuri = best_fit(uri, available_fit[keyuri])
            chrome[newuri] = stream
        else:
            if stream["error"] != "404":
                print(keyuri, stream, "unknown", file=sys.stderr)
    
    ff = {}
    for stream in firefox_streams:
        uri = stream["url"]
        keyuri = uri.split('?',1)[0]
        if keyuri in available_fit:
            newuri = best_fit(uri, available_fit[keyuri])
            ff[newuri] = stream
        else:
            if stream["error"] != "404":
                print(keyuri, stream, "unknown", file=sys.stderr)
    
    t = {}
    for uri, p in chrome_types.items():
        if uri.startswith("http"):
            keyuri = uri.split('?',1)[0].split("//",1)[1]
            if keyuri in available_fit:
                newuri = best_fit(uri, available_fit[keyuri])
                t[newuri] = p

    ff_classes.append(classify_firefox_prio(ff))
    chrome_classes.append(classify_chrome_prio(chrome))
    types.append(t)

def fuse_ff(dicts):
    mapping = {
        "urgent-start": 6,
        "leaders": 5,
        "followers": 4,
        "unblocked": 3,
        "background": 2,
        "speculative": 1
    }
    out = {}
    keys = set()
    for d in dicts:
        keys |= set(d.keys())
    for key in keys:
        entries = [d[key] for d in dicts if key in d]
        a = entries[0]
        for b in entries:
            if mapping[b["c"]] > mapping[a["c"]]:
                a["c"] = b["c"]
            if b["w"] > a["w"]:
                a["w"] = b["w"]
        out[key] = a
    return out

def fuse_type(dicts):
    out = {}
    for key in set([k for d in dicts for k in d.keys()]):
        entries = [d[key] for d in dicts if key in d]
        a = entries[0]
        for b in entries:
            if a == "unknown" and b == "xhr":
                a = "xhr"
            elif b == "unknown" and a == "xhr":
                b = "xhr"
            elif b == "js" and a == "xhr":
                a = "js"
            elif a == "js" and b == "xhr":
                b = "js"
            assert b == a, ("class mismatch", key, b, a)
        out[key] = a
    return out

def fuse_chrome(dicts):
    mapping = {
        "highest": 7,
        "high": 6,
        "normal": 5,
        "low": 4,
        "lowest": 3,
        "idle": 2,
        "throttled": 1
    }
    out = {}
    for key in set([k for d in dicts for k in d.keys()]):
        entries = [d[key] for d in dicts if key in d]
        a = entries[0]
        for b in entries:
            if mapping[b] > mapping[a]:
                a = b
        out[key] = a
    return out

ff_classes = fuse_ff(ff_classes)
chrome_classes = fuse_chrome(chrome_classes)
types = fuse_type(types)

out = []

for uri in (set(ff_classes.keys()) | set(chrome_classes.keys())):

    firefox_prio_class = "background"
    firefox_prio_weight = 12
    chrome_prio_class = "lowest"
    resource_type = "unknown"

    if uri in ff_classes:
        firefox_prio_class = ff_classes[uri]["c"]
        firefox_prio_weight = ff_classes[uri]["w"]

    if uri in chrome_classes:
        chrome_prio_class = chrome_classes[uri]
    
    if uri in types:
        resource_type = types[uri]

    assert not "#" in uri, uri
    out.append("GET:%s#%s#%s#%s#%d"%(uri, resource_type, chrome_prio_class, firefox_prio_class, firefox_prio_weight))
    
with open(output, "w") as f:
    f.write("\n".join(sorted(out)))