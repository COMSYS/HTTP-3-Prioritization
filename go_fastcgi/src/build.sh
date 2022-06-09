#!/bin/bash
SCRIPT=`realpath -s $0`
SCRIPTPATH=`dirname $SCRIPT`
GOPATH=$HOME/go:$SCRIPTPATH/.. go build
mv src fcgi