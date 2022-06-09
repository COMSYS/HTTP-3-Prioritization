import json
import sys
import gzip
import numpy as np
from collections import Counter

def hol_compute(netlogfile):

    total_stream_hol = 0
    total_conn_hol = 0
    total_packets = 0
    total_packets_lost = 0

    errors = []

    if netlogfile.endswith(".gz"):
        opener = gzip.open
    else:
        opener = open

    with opener(netlogfile) as f:
        text = f.read()
        try:
            text = text.decode()
        except:
            pass
        #truncated netlog? try to fix it
        while text[-1] in ["\n", " ", ","]:
            text = text[:-1]
        if not text[-2:] == "]}":
            text = text + "]}"
        netlog = json.loads(text)

    types = netlog["constants"]["logEventTypes"]
    type_map = {value:key for key, value in types.items()}

    quic_sessions = {}

    #identify quic connections and log packets
    for event in netlog["events"]:
        event["type"] = type_map[event["type"]]
        if event["type"] == "QUIC_SESSION" and event["phase"] == 1:
            assert not event["source"]["id"] in quic_sessions
            quic_sessions[event["source"]["id"]] = event
            event["packets"] = []
        if event["type"] == "QUIC_SESSION_CLOSED":
            qs = quic_sessions[event["source"]["id"]]
            qs["closed"] = event["params"]["details"]
        elif event["type"] == "QUIC_SESSION_UNAUTHENTICATED_PACKET_HEADER_RECEIVED":
            qs = quic_sessions[event["source"]["id"]]
            qs["latest_pnr"] = event["params"]["packet_number"]        
            if len(qs["packets"]) <= qs["latest_pnr"]:
                qs["packets"] += [None] * (qs["latest_pnr"] + 1 - len(qs["packets"]))
            qs["packets"][qs["latest_pnr"]] = []
        elif event["type"] == "QUIC_SESSION_STREAM_FRAME_RECEIVED":
            qs = quic_sessions[event["source"]["id"]]
            params = event["params"]
            params["time"] = event["time"]
            qs["packets"][qs["latest_pnr"]].append(params)

    #process quic conns
    for id, session in quic_sessions.items():
        error = "okay"
        if "closed" in session:
            error = session["closed"]
            #assert session["closed"] not in ["Network blackhole detected","header value too long"]
        packets = session["packets"]

        def missing_segments(stream_id, missing, new):
            news, newe = new
            assert news < newe, new
            o = []
            unseen_bytes = 0
            for s, e in missing:
                if newe <= s:
                    o.append((s,e))
                elif news >= e:
                    o.append((s,e))
                elif news <= s and newe >= e:
                    unseen_bytes += e - s 
                elif news > s and newe < e:
                    o.append((s,news))
                    o.append((newe,e))
                    unseen_bytes += newe - news
                elif news > s and news < e and newe >= e:
                    o.append((s,news))
                    unseen_bytes += e - news
                elif news <= s and newe > s and newe < e:
                    o.append((newe, e))
                    unseen_bytes += newe - s
                else:
                    assert False, (missing, new)
            return o, unseen_bytes
        
        conn_hol_blocking = 0
        stream_hol_blocking = 0
        connection_missing = {}
        conn_lost = 0

        #find stream holes
        for packet in packets:
            if packet is None:
                #lost packet
                conn_lost += 1
            else:
                for frame in packet:
                    stream_id = frame["stream_id"]
                    if not stream_id in connection_missing:
                        connection_missing[stream_id] = {"missing":[(0, np.inf)],"blocked":[],"hol_blocked":False, "stream_id":stream_id}
                    if frame["length"] != 0:
                        before = connection_missing[stream_id]["missing"]
                        after, unseen = missing_segments(stream_id, before, (frame["offset"], frame["offset"]+frame["length"]))
                        connection_missing[stream_id]["missing"] = after

                        if before[0][0] == after[0][0]:
                            connection_missing[stream_id]["hol_blocked"] = True
                            stream_hol_blocking += unseen
                            conn_hol_blocking += unseen
                            for stream in connection_missing.values():
                                if stream_id != stream["stream_id"]:
                                    stream["blocked"].append((connection_missing[stream_id], frame["offset"], stream["missing"][-1][0]))
                        else:
                            connection_missing[stream_id]["hol_blocked"] = False
                            if any([blocked_stream["missing"][0][0] < offset and frame["offset"] > my_offset  for blocked_stream, offset, my_offset in connection_missing[stream_id]["blocked"]]):
                                conn_hol_blocking += unseen
        
        errors.append(error)
        total_stream_hol += stream_hol_blocking
        total_conn_hol += conn_hol_blocking
        total_packets += len(packets)
        total_packets_lost += conn_lost

    #check if multiple concurrent connections existed, which were not correctly identified
    errors_count = Counter(errors)
    valid = 0 if any([not error in ["okay", "An active session exists for the given IP."] for error in errors]) or (errors_count.get("okay",0) != 1) else 1

    assert valid == 1

    return {"stream_hol":total_stream_hol, "conn_hol":total_conn_hol, "packets":total_packets, "packets_lost":total_packets_lost}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: %s chromenetlog")
    else:
        print(hol_compute(sys.argv[1]))