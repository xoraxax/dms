#!/bin/sh
set -e
echo Generating index data for $1 ...
mkdir -p index
tr -s '[[:punct:][:space:]]' '\n' < "${1%.pdf}.txt" | sed 's/.*/\L&/' | awk 'length($0) <= 40 && length($0) >= 3' - | sort | uniq > "${1%.pdf}.words"
cd index
while read -r WORD; do
  echo "${1%.pdf}">>"$WORD"
done < "../${1%.pdf}.words"
