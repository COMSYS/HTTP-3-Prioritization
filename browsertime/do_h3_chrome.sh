CHROMEPATH="/tmp/chrome$(date +%s%N)"
BROWSERTIMEPATH="/browsertime"

docker exec $2-browsertime find $BROWSERTIMEPATH -mindepth 1 -delete
docker exec $2-browsertime mkdir $CHROMEPATH

cp $4 /tmp/browsertime-$2

docker exec $2-browsertime node /usr/src/app/bin/browsertime.js \
    --chrome.args "user-data-dir=$CHROMEPATH" \
    --resultDir $BROWSERTIMEPATH \
    --xvfb true \
    --chrome.collectNetLog true \
    --chrome.args "ignore-privacy-mode" \
    --chrome.args "enable-quic" \
    --chrome.args "quic-version=h3" \
    --chrome.args "origin-to-force-quic-on=*" \
    --useSameDir true \
    --iterations 1 \
    --script /browsertime/script.js \
    "$1" > /tmp/browsertime-$2/docker.log

docker exec $2-browsertime rm -rf $CHROMEPATH