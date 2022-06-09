CHROMEPATH="/tmp/chrome$(date +%s%N)"
BROWSERTIMEPATH="/browsertime"

docker exec $2-browsertime find $BROWSERTIMEPATH -mindepth 1 -delete
docker exec $2-browsertime mkdir $CHROMEPATH

docker exec $2-browsertime node /usr/src/app/bin/browsertime.js \
    --chrome.binaryPath "/opt/comsyschrome/chrome" \
    --chrome.chromedriverPath "/opt/comsyschrome/chromedriver" \
    --chrome.args "user-data-dir=$CHROMEPATH" \
    --chrome.collectPerfLog true \
    --resultDir $BROWSERTIMEPATH \
    --chrome.args "disable-field-trial-config" \
    --xvfb true \
    --video false \
    --chrome.args "ignore-privacy-mode" \
    --visualMetrics false \
    --chrome.args "disable-quic" \
    --pageCompleteCheckInactivity true \
    --pageCompleteWaitTime 30000 \
    --chrome.enableChromeDriverLog true \
    --pageLoadStrategy "normal" \
    -n 1\
    --useSameDir true\
    "$1" > /tmp/browsertime-$2/docker.log

docker exec $2-browsertime rm -rf $CHROMEPATH
