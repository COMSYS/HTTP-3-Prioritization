#!/bin/bash
Xvfb :99 -screen 0 1280x960x24 &
export DISPLAY=:99
export CHROME_PATH="/opt/google/chrome/chrome"
lighthouse "$@" --chrome-flags="--headless --no-sandbox --disable-gpu --ignore-privacy-mode --ignore-certificate-errors --quic-version=h3 --origin-to-force-quic-on=* --enable-quic --log-net-log=/lighthouse/netlog.json" > /lighthouse/log 2>&1
