#!/bin/bash
CNF="[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn
[dn]
C = US
ST = CA
L = US
O = h2o
OU = h2o
CN = $2
[req_ext]
subjectAltName = @alt_names
[alt_names]
DNS.1 = $2"

SCRIPT=`realpath -s $0`
SCRIPTPATH=`dirname $SCRIPT`

FILE="$1"
i=2

shift 2

for var in "$@"
do
    CNF=$(echo -ne "$CNF\nDNS.$i = $var")
    i=$((i + 1))
done

openssl genrsa -out $FILE.key 2048
openssl req -new -sha256 -key $FILE.key -config <( echo "$CNF" ) -out $FILE.csr
openssl x509 -req -in $FILE.csr -CA $SCRIPTPATH/RootCA.crt -CAkey $SCRIPTPATH/RootCA.key -out $FILE.crt -days 500 -sha256 -extfile <( echo "$CNF" ) -extensions req_ext