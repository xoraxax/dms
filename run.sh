#!/bin/sh
. env/bin/activate
DMSDATA=db FLASK_APP=dms.py flask run "$@"
