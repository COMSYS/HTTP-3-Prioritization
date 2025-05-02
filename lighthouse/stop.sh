#!/bin/bash
set -e
docker stop $1-lighthouse
rm /var/run/netns/$1-docker
rm -rf /tmp/lighthouse-$1