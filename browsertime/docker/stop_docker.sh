#!/bin/bash
set -e
docker stop $1-browsertime
rm /var/run/netns/$1-docker
rm -rf /tmp/browsertime-$1