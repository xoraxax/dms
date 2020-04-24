# (c) 2019 Alexander Schremmer <alex@alexanderweb.de>
# Licensed under AGPL v3.

import cgi
import glob
import logging
import os
import queue
import re
import threading
import time

from flask import Flask, redirect, url_for, send_from_directory, request
from werkzeug.utils import secure_filename


logging.basicConfig()
app = Flask(__name__)
DATA_DIR = os.path.abspath(os.environ["DMSDATA"])
SOURCE_DIR = os.readlink(os.path.join(DATA_DIR, "SOURCE_DIR"))
IMPORTER = os.path.abspath(os.path.join(__file__, "..", "importer.sh"))
DELAY = 45
FILE_QUEUE = queue.Queue()


class DirReaderThread(threading.Thread):
    def run(self):
        files = {}
        while True:
            time.sleep(1)
            for fname in glob.glob(os.path.join(SOURCE_DIR, "*.pdf")):
                t = time.time()
                if files.setdefault(fname, t + DELAY) < t:
                    del files[fname]
                    FILE_QUEUE.put(fname)


class ImporterThread(threading.Thread):
    def run(self):
        while True:
            fname = FILE_QUEUE.get()
            # XXX use subprocess
            os.system('"%s" "%s" "%s"' % (IMPORTER, fname, DATA_DIR))


@app.before_first_request
def boot_thread():
    ImporterThread().start()
    DirReaderThread().start()


def search(q):
    if not q:
        yield from (
            os.path.basename(x).rsplit(".", 1)[0]
            for x in glob.glob(os.path.join(DATA_DIR, "*.txt"))
        )
    else:
        res = [re.compile(segment, re.I | re.U) for segment in q.split()]
        for fname in glob.glob(os.path.join(DATA_DIR, "*.txt")) + glob.glob(
            os.path.join(DATA_DIR, "*.desc")
        ):
            data = open(fname).read()
            if all(regex.search(data) for regex in res):
                yield os.path.basename(fname).rsplit(".", 1)[0]


def heading(s):
    return "<h1><a href='/'>" + cgi.escape(s, quote=True) + "</a></h1>"


def search_box(q):
    return (
        '<form><input type="text" value="%s" name="q" placeholder="Search query"><input type="submit" value="Search"></form>'
        % cgi.escape(q, quote=True)
    )


def listofdir(func, filter_to):
    filter_to = sorted(filter_to, reverse=True)
    rv = ["<ul>"]
    for fname in filter_to:
        rv.append("<li style='display: inline-block; padding: 1em;'>")
        rv.append(func(fname))
        rv.append("</li>")
    rv.append("</ul>")
    return "".join(rv)


def link_list(es):
    rv = ["<ul style='display: block; padding: 1em; '>"]
    for e in es:
        rv.append("<li>")
        rv.append(e)
        rv.append("</li>")
    rv.append("</ul>")
    return "".join(rv)


def flink(title, method, arg):
    return "<a target='_blank' href='%s'>%s</a>" % (url_for(method, name=arg), title)


def render_page(l):
    s = """
img {
    padding: 1em;
    background-color: lightgray;
}

img.small {
    height: 200px;
}

img.redflag {
    background-color: orange;
}
"""
    return (
        "<html><head><title>DMS</title><style>%s</style></head><body>%s</body></html>"
        % (s, "\n".join(l))
    )


def compute_img_class(fname):
    path = os.path.join(DATA_DIR, fname)
    if os.path.exists(path + ".desc"):
        return ""
    return "redflag"


def page_count(fname):
    path = os.path.join(DATA_DIR, fname) + ".count"
    if os.path.exists(path):
        return int(open(path).read())
    return 0


@app.route("/edit/<name>", methods="GET POST".split())
def edit(name):
    origname = name
    basename = os.path.join(DATA_DIR, secure_filename(name))
    descname = basename + ".desc"
    try:
        data = open(descname).read()
    except OSError:
        data = ""
    q = request.form.get("value", None)
    if q is None:
        return render_page(
            [
                heading("DMS - %s (%i pages)" % (origname, page_count(origname))),
                '<form method=POST><textarea name="value" rows="10" cols="80" placeholder="Title and description here">%s</textarea><input type="submit" value="Save"></form>%s<img src="%s">'
                % (
                    cgi.escape(data, quote=True),
                    link_list(
                        [
                            flink("view OCRed", "download", origname + ".pdf"),
                            flink("view original", "download", origname + ".orig.pdf"),
                        ]
                    ),
                    url_for("download", name=origname + ".png"),
                ),
            ]
        )
    else:
        open(descname, "w").write(q)
        return redirect(url_for("root"))


@app.route("/download/<name>")
def download(name):
    return send_from_directory(DATA_DIR, name)


@app.route("/")
def root():
    q = request.args.get("q", "")
    filter_to = set(search(q))
    return render_page(
        [
            heading(("DMS - '%s'" % (q,)) if q else "DMS"),
            search_box(q),
            listofdir(
                lambda fname: '<a href="%s"><img title="%i pages" class="small %s" src="%s"></a>'
                % (
                    url_for("edit", name=fname),
                    page_count(fname),
                    compute_img_class(fname),
                    url_for("download", name=fname + ".png"),
                ),
                filter_to=filter_to,
            ),
        ]
    )
