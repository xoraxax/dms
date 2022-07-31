# (c) 2019 Alexander Schremmer <alex@alexanderweb.de>
# Licensed under AGPL v3.

import glob
import html
import itertools
import logging
import os
import queue
import re
import subprocess
import threading
import time

from flask import Flask, redirect, url_for, send_from_directory, request
from werkzeug.utils import secure_filename


logging.basicConfig()
app = Flask(__name__)
DATA_DIR = os.path.abspath(os.environ["DMSDATA"])
SUB_DATA_DIRS = sorted(os.path.basename(path) for path in (os.path.join(DATA_DIR, path) for path in os.listdir(DATA_DIR)) if os.path.isdir(path) and not os.path.islink(path))
SOURCE_DIR = os.readlink(os.path.join(DATA_DIR, "SOURCE_DIR"))
IMPORTER = os.path.abspath(os.path.join(__file__, "..", "importer.sh"))
DELAY = 45
FILE_QUEUE = queue.Queue()
RE_TAG = re.compile(r"#[^\s]*", re.U)


class DirReaderThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.files = {}

    def remove(self, fname):
        del self.files[fname]

    def run(self):
        while True:
            time.sleep(1)
            for fname in glob.glob(os.path.join(SOURCE_DIR, "*.pdf")):
                t = time.time()
                if fname in self.files:
                    if self.files[fname] and self.files[fname] < t:
                        FILE_QUEUE.put((fname, lambda fname=fname: self.remove(fname)))
                        self.files[fname] = None
                else:
                    self.files[fname] = t + DELAY


class ImporterThread(threading.Thread):
    def run(self):
        while True:
            fname, finalizer = FILE_QUEUE.get()
            subprocess.run([IMPORTER, fname, app.data_dir])
            finalizer()


@app.before_first_request
def boot_thread():
    app.data_dir = os.path.join(DATA_DIR, SUB_DATA_DIRS[0]) if SUB_DATA_DIRS else DATA_DIR
    ImporterThread().start()
    DirReaderThread().start()


def search(q):
    if not q:
        yield from (
            os.path.basename(x).rsplit(".", 1)[0]
            for x in glob.glob(os.path.join(app.data_dir, "*.txt"))
        )
    else:
        res = [re.compile(segment, re.I | re.U) for segment in q.split()]
        for fname in itertools.chain(*[glob.glob(os.path.join(app.data_dir, pattern)) for pattern in ("*.txt", "*.desc", "*.fname")]):
            data = open(fname).read()
            if all(regex.search(data) for regex in res):
                yield os.path.basename(fname).rsplit(".", 1)[0]


def heading(s):
    return "<h1><a href='/'>" + html.escape(s, quote=True) + "</a></h1>"


def change_tenant():
    return "<form action='/'><label>Tenant: <select onchange='this.form.submit();' name='tenant' size='1'>%s</select></label></form>" % (
            "\n".join("<option%s>%s</option>" % (" selected" if path == os.path.basename(app.data_dir) else "", path) for path in SUB_DATA_DIRS),
    )


def search_box(q):
    return (
        '<form><input type="text" value="%s" name="q" placeholder="Search query"><input type="submit" value="Search"></form>'
        % html.escape(q, quote=True)
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

def search_link(query):
    return "<a href='%s'>%s</a>" % (url_for("root", q=query), html.escape(query))


def render_page(l):
    s = """
img {
    padding: 1em;
    border: 8px solid lightgray;
}

img.small {
    height: 200px;
}

img.redflag {
    border-color: orange;
}

a:link {
    text-decoration: none;
}
"""
    return (
        "<html><head><title>DMS</title><style>%s</style></head><body>%s</body></html>"
        % (s, "\n".join(l))
    )


def compute_img_class(fname):
    path = os.path.join(app.data_dir, fname)
    if os.path.exists(path + ".desc"):
        return ""
    return "redflag"


def page_count(fname):
    path = os.path.join(app.data_dir, fname) + ".count"
    if os.path.exists(path):
        return int(open(path).read())
    return 0


def original_filename(fname):
    path = os.path.join(app.data_dir, fname) + ".fname"
    if os.path.exists(path):
        return open(path).read()
    return ""


@app.route("/edit/<name>", methods="GET POST".split())
def edit(name):
    origname = name
    basename = os.path.join(app.data_dir, secure_filename(name))
    descname = basename + ".desc"
    try:
        data = open(descname).read()
    except OSError:
        data = ""
    q = request.form.get("value", None)
    if q is None:
        tags = RE_TAG.findall(data)
        return render_page(
            [
                heading("DMS%s: %s (%i pages) %s" % (tenant_suffix(), origname, page_count(origname), original_filename(origname))),
                '<form method=POST><textarea name="value" rows="10" cols="80" placeholder="Title and description here">%s</textarea><input type="submit" value="Save"></form>%s<img src="%s">'
                % (
                    html.escape(data, quote=True),
                    link_list(
                        [
                            flink("view OCRed", "download", origname + ".pdf"),
                            flink("view original", "download", origname + ".orig.pdf"),
                        ]
                    ),
                    url_for("download", name=origname + ".png"),
                ),
                ("<h2>Tag search</h2>" + link_list([search_link(tag) for tag in tags])) if tags else "",
            ]
        )
    else:
        open(descname, "w").write(q)
        return redirect(url_for("root"))


@app.route("/download/<name>")
def download(name):
    return send_from_directory(app.data_dir, name)


def tenant_suffix():
    return " [%s] " % os.path.basename(app.data_dir) if SUB_DATA_DIRS else ""


@app.route("/")
def root():
    tenant = request.args.get("tenant", "")
    if tenant and tenant in SUB_DATA_DIRS:
        app.data_dir = os.path.join(DATA_DIR, tenant)
        return redirect(url_for("root"))
    q = request.args.get("q", "")
    filter_to = set(search(q))
    return render_page(
        [
            heading("DMS%s%s" % (tenant_suffix(), ": searching for '%s'" % q if q else "")),
            change_tenant() if SUB_DATA_DIRS else "",
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
