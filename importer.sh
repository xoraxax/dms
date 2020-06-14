#!/bin/sh

#set -x

FILE="$1"
OUTPUT="$2"

mtime=$(stat -c '%Y' "$FILE")
newname=$(date -d "@$mtime" -Iseconds | tr :+ __)
newname="$OUTPUT/$newname.pdf"
mv "$FILE" "$newname"
pdfsandwich -lang deu+eng "$newname"
mv "$newname" "${newname%.pdf}.orig.pdf"
mv "${newname%.pdf}_ocr.pdf" "$newname"
pdfinfo "$newname" | grep Pages: | sed 's/[^0-9]*//' >"${newname%.pdf}.count"
convert -thumbnail x600 "${newname%.pdf}.orig.pdf[0]" "${newname%.pdf}.png"
pdftotext "$newname"
