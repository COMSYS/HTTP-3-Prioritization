#!/bin/bash
docker exec $2-lighthouse bash /lighthouse/lighthouse-xvfb.sh $1 --config-path=/lighthouse/lighthousecfg.js --output=json --output-path=/lighthouse/lighthouse-report.json

# --only-audits="speed-index,first-contentful-paint,largest-contentful-paint,cumulative-layout-shift,total-blocking-time"
