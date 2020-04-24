#!/bin/sh
mtime=`stat -c '%Y' $1`
newname=`date -d "@$mtime" -Iseconds | tr :+ __`
newname="$2/$newname.pdf"
mv "$1" "$newname"
pdfsandwich -lang deu+eng "$newname"
mv "$newname" "${newname%.pdf}.orig.pdf"
mv "${newname%.pdf}_ocr.pdf" "$newname"
pdfinfo "$newname" | grep Pages: | sed 's/[^0-9]*//' > "${newname%.pdf}.count"
convert -thumbnail x600 "${newname%.pdf}.orig.pdf[0]" "${newname%.pdf}.png"
pdftotext "$newname"
