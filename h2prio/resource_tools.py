import json
import csv
import traceback

firefox_phantom_nodes = {
    3: "leaders",
    11: "followers",
    5: "unblocked",
    7: "background",
    9: "speculative",
    13: "urgent-start"
}

chrome_weight_buckets = {
    256: "highest",
    220: "high",
    183: "normal",
    147: "low",
    110: "lowest",
    74: "idle",
    37: "throttled"
}

def get_resource_streams(content):
    streams = []
    for entries in csv.reader(content.split("\n"), delimiter=" "):
        if len(entries) > 0:
            assert len(entries) == 13

            url = entries[5].split(" ")[1]
            method = entries[5].split(" ")[0]
            url = url.replace("\\x7e","~")
            url = url.replace("\\x7d","}")
            error = entries[6]
            host = entries[12]
            weight = entries[10]
            parent = entries[11]
            streams.append({"w":int(weight), "dep": int(parent), "url": host + url, "method": method, "error": error})

    return streams

def get_resource_prio(content):
    streams = get_resource_streams(content)

    prio = {}

    for stream in streams:
        if not "url" in stream:
            #firefox creates stream without resources
            continue
        url = stream["url"]
        if url in prio:
            assert stream["w"] == prio[url]["w"]
        del stream["url"]
        prio[url] = stream
    
    return prio


chrome_resource_map = {
    "Document": "html",
    "Script": "js",
    "Stylesheet": "css",
    "Media": "image",
    "XHR": "xhr",
    "Fetch": "xhr",
    "Font": "fonts",
    "Image": "image",
    "Other": "unknown",
    "Ping": "ping",
    "Manifest": "xhr",
    "service_worker": "js",
    "worker": "js",
    "TextTrack": "image",
    "iframe": "iframe"
}

def get_resource_types(content):
    types = {}
    perflog = json.loads(content)
    for params in perflog:
        if "type" in params:
            type = params["type"]
            url = params["request"]["url"]
            if url.startswith("data"):
                continue
            if type in chrome_resource_map:
                types[url] = chrome_resource_map[type]
            else:
                assert False, ("unknown type %s" % type)
        elif "targetInfo" in params:
            targetInfo = params["targetInfo"]
            url = targetInfo["url"]
            if len(url) > 0:
                type = targetInfo["type"]
                if type in chrome_resource_map:
                    types[url] = chrome_resource_map[type]
                else:
                    assert False, ("unknown type %s" % type)
    return types


def classify_chrome_prio(chrome_prio):
    out = {}
    for url, prio in chrome_prio.items():
        if prio["w"] in chrome_weight_buckets:
            out[url] = chrome_weight_buckets[prio["w"]]
        else:
            assert False, (url,prio)
    return out

def classify_firefox_prio(firefox_prio):
    return {url:{"c":firefox_phantom_nodes[prio["dep"]],"w":prio["w"]} for url, prio in firefox_prio.items()}