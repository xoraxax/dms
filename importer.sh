#!/bin/sh
set -e
mtime=`stat -c '%Y' "$1"`
oldname=`basename "$1"`
newbasename=`date -d "@$mtime" -Iseconds | tr :+ __`
newname="$2/$newbasename.pdf"
mv "$1" "$newname"
pdfsandwich -lang deu+eng "$newname"
mv "$newname" "${newname%.pdf}.orig.pdf"
mv "${newname%.pdf}_ocr.pdf" "$newname"
pdfinfo "$newname" | grep Pages: | sed 's/[^0-9]*//' > "${newname%.pdf}.count"
convert -thumbnail x600 "${newname%.pdf}.orig.pdf[0]" "${newname%.pdf}.png"
pdftotext "$newname"
echo -n "$oldname"> "${newname%.pdf}.fname"
tr -s '[[:punct:][:space:]]' '\n' < "${newname%.pdf}.txt" | sed 's/.*/\L&/' | awk 'length($0) <= 40 && length($0) >= 3' - | sort | uniq > "${newname%.pdf}.words"
mkdir -p "$2/index"
while read -r WORD; do
  echo "${newname%.pdf}">>"$2/index/$WORD"
done < "${newname%.pdf}.words"
