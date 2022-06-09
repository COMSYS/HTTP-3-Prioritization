#!/bin/bash
SCRIPT=`realpath -s $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH
./fcgi $1 $2 $3 &