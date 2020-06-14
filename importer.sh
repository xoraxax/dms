#!/usr/bin/env bash

#set -x
set -e
set -o pipefail

FILE="$1"
OUTPUT="$2"
ERROR_OUTPUT="${3:-${OUTPUT}_error}"
TEMP_FOLDER=$(mktemp -d)

create_folder() {
  local folder="$1"
  if [[ -d "$folder" ]]; then
    return
  fi
  if [[ -e "$folder" ]]; then
    echo "$folder exists but is not a folder"
    exit 1
  fi
  mkdir -p "$folder"
}

create_folder "$OUTPUT"
create_folder "$ERROR_OUTPUT"

mtime=$(stat -c '%Y' "$FILE")
filename=$(date -d "@$mtime" -Iseconds | tr :+ __).pdf
filepath="$TEMP_FOLDER/$filename"

cleanup() {
  echo "move file to error folder $ERROR_OUTPUT"
  mv "$FILE" "$ERROR_OUTPUT/$filename"
  rm -rf "$TEMP_FOLDER"
}
trap cleanup 0

cp "$FILE" "$filepath"
pdfsandwich -lang deu+eng "$filepath"
mv "$filepath" "${filepath%.pdf}.orig.pdf"
mv "${filepath%.pdf}_ocr.pdf" "$filepath"
pdfinfo "$filepath" | grep Pages: | sed 's/[^0-9]*//' >"${filepath%.pdf}.count"
convert -thumbnail x600 "${filepath%.pdf}.orig.pdf[0]" "${filepath%.pdf}.png"
pdftotext "$filepath"

set -x
mv "$TEMP_FOLDER"/* "$OUTPUT/"
set +x

rm "$FILE"
trap "" 0
