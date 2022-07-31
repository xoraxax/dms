#!/bin/sh
set -e
echo 'Run this in the tenant folders or the db folder of your DMS instance to generate the similarity index.'
if [ -d index ]; then
  echo index folder already exists!
  exit 1
fi
echo Generating index for data directory `pwd` ...
TOOL=`dirname "$0"`/add_words.sh
for I in *00.pdf; do "$TOOL" "$I"; done
