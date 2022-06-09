#!/bin/bash
set -e
docker stop $1-browsertime
rm /var/run/netns/$1-browsertime