#!/bin/bash
set -e
mkdir -p /tmp/lighthouse-$1
cp /home/veltri/bo-prioritization-sandbox/testbed/lighthouse/lighthousecfg.js /tmp/lighthouse-$1
cp /home/veltri/bo-prioritization-sandbox/testbed/lighthouse/lighthouse-xvfb.sh /tmp/lighthouse-$1
docker run --shm-size=4g --rm -it -d --network=none --entrypoint "/bin/bash" -v "/tmp/lighthouse-$1":/lighthouse --dns 10.0.1.4 --cap-add=SYS_NICE --name $1-lighthouse lighthouse:latest
DPID=$(docker inspect -f '{{.State.Pid}}' $1-lighthouse)
mkdir -p /var/run/netns
ln -s /proc/$DPID/ns/net /var/run/netns/$1-docker
