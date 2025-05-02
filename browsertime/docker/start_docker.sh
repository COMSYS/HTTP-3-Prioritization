#!/bin/bash
set -e
mkdir -p /tmp/browsertime-$1
docker run --shm-size=4g --rm -it -d  --network=none --entrypoint "/bin/bash" -v "/tmp/browsertime-$1":/browsertime --dns 10.0.1.4 --cap-add=SYS_NICE --name $1-browsertime laboratory.comsys.rwth-aachen.de:5050/students-sander/ma-dario-veltri/code/browsertime-docker
DPID=$(docker inspect -f '{{.State.Pid}}' $1-browsertime)
mkdir -p /var/run/netns
ln -s /proc/$DPID/ns/net /var/run/netns/$1-docker