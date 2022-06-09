CHROMEPATH="/tmp/chrome$(date +%s%N)"
BROWSERTIMEPATH="/browsertime"

docker exec $2-browsertime find $BROWSERTIMEPATH -mindepth 1 -delete
docker exec $2-browsertime mkdir $CHROMEPATH

docker exec $2-browsertime node /usr/src/app/bin/browsertime.js \
    --chrome.binaryPath "/opt/comsyschrome/chrome" \
    --chrome.chromedriverPath "/opt/comsyschrome/chromedriver" \
    --chrome.args "user-data-dir=$CHROMEPATH" \
    --resultDir $BROWSERTIMEPATH \
    --chrome.args "disable-field-trial-config" \
    --xvfb true \
    --chrome.args "ignore-privacy-mode" \
    --chrome.args "enable-quic" \
    --chrome.args "quic-version=h3" \
    --chrome.args "origin-to-force-quic-on=*" \
    --chrome.collectNetLog true \
    --timeouts.pageCompleteCheck $3 \
    --timeouts.pageLoad $3 \
    --visualMetrics \
    -n 1 \
    --videoParams.framerate 50 \
    --videoParams.createFilmstrip false \
    --useSameDir true\
    "$1" > /tmp/browsertime-$2/docker.log

docker exec $2-browsertime rm -rf $CHROMEPATH