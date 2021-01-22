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
    """looks for files that have a ctime which is older than DELAY
    and runs import.sh on them"""

    def run(self):
        files = {}
        while True:
            time.sleep(1)
            for filename in glob.glob(os.path.join(SOURCE_DIR, "*.pdf")):
                current_time = time.time()
                if files.setdefault(filename, current_time + DELAY) < current_time:
                    del files[filename]
                    FILE_QUEUE.put(filename)


class ImporterThread(threading.Thread):
    def run(self):
        while True:
            filename = FILE_QUEUE.get()
            # XXX use subprocess
            os.system('"%s" "%s" "%s"' % (IMPORTER, filename, DATA_DIR))


@app.before_first_request
def boot_thread():
    ImporterThread().start()
    DirReaderThread().start()


def search(query):
    if not query:
        yield from (
            os.path.basename(x).rsplit(".", 1)[0]
            for x in glob.glob(os.path.join(DATA_DIR, "*.txt"))
        )
    else:
        res = [re.compile(segment, re.I | re.U) for segment in query.split()]
        for filename in glob.glob(os.path.join(DATA_DIR, "*.txt")) + glob.glob(
                os.path.join(DATA_DIR, "*.desc")
        ):
            data = open(filename).read()
            if all(regex.search(data) for regex in res):
                yield os.path.basename(filename).rsplit(".", 1)[0]


def heading(s):
    return "<h1><a href='/'>" + cgi.html.escape(s, quote=True) + "</a></h1>"


def search_box(q):
    return (
            """
            <form id="search">
              <input class=input type="text" value="%s" name="q" placeholder="Search query" autofocus>
              <input class=button type="submit" value="Search">
            </form>""" % cgi.html.escape(q, quote=True)
    )


def list_of_directories(func, filter_to):
    filter_to = sorted(filter_to, reverse=True)
    result = ["<ul>"]
    for filename in filter_to:
        result.append("<li style='display: inline-block; padding: 1em;'>")
        result.append(func(filename))
        result.append("</li>")
    result.append("</ul>")
    return "".join(result)


def link_list(items, attributes='class="list_items"'):
    result = [("<ul %s>" % attributes)]
    for item in items:
        result.append("<li>")
        result.append(item)
        result.append("</li>")
    result.append("</ul>")
    return "".join(result)


def link_item(title, method, arg):
    return "<a class=button target='_blank' href='%s'>%s</a>" % (url_for(method, name=arg), title)


def render_page(body):
    s = """
img {
    padding: 1em;
    background-color: lightgray;
}

img.small {
    height: 200px;
}

img.red_flag {
    background-color: orange;
}

#search {
    width: 800px;
    margin-left: auto;
    margin-right: auto;
    display: grid;
    grid-template-columns: auto 200px;
    grid-template-rows: auto;
    grid-template-areas: "input button";
}
#search > .input {
    grid-area: input;
    margin-right: 5px;
    padding-left: 11px;
}
#search > .button {
    grid-area: button;
}

#edit {
    width: 800px;
    margin-left: auto;
    margin-right: auto;
    display: grid;
    grid-template-columns: 220px 580px;
    grid-template-rows: auto;
    grid-template-areas:
    "description description"
    "downloads preview";
}
#edit > .description {
    grid-area: description;
}
#edit > .list_items{
    grid-area: downloads;
    margin-left:auto;
    padding: 0px;
}
#edit > .preview{
    grid-area: preview;
    margin-left:auto;
    margin-right:auto;
}

.description {
    display: grid;
    grid-template-columns: auto 200px;
    grid-template-rows: auto;
    grid-template-areas:
    "input input"
    ". button";
}
.description > .input {
    grid-area: input;
    height: 100px;
    padding-left: 10px;
    padding-top: 8px;
    padding-right: 6px;
}
.description > .button{
    grid-area: button;
    margin-top: 5px;
}

.button {
    background-color: #4CAF50; /* Green */
    color: white;
    transition-duration: 0.4s;
    border: none;
    padding: 12px 28px;
    text-decoration: none;
}
.button:hover {
    background-color: #dcefdc;
    color: #4CAF50;
}

.list_items {
    list-style: none;
}
.list_items li {
    margin-bottom: 30px;
    text-align: right;
}
"""
    return (
            """
            <html>
            <head>
            <title>DMS</title>
            <style>%s</style>
            </head>
            <body>%s</body>
            </html>
            """
            % (s, "\n".join(body))
    )


def compute_img_class(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path + ".desc"):
        return ""
    return "red_flag"


def page_count(filename):
    path = os.path.join(DATA_DIR, filename) + ".count"
    if os.path.exists(path):
        return int(open(path).read())
    return 0


@app.route("/edit/<name>", methods="GET POST".split())
def edit(name):
    original_name = name
    basename = os.path.join(DATA_DIR, secure_filename(name))
    description_file = basename + ".desc"
    try:
        data = open(description_file).read()
    except OSError:
        data = ""
    query = request.form.get("value", None)
    if query is None:
        return render_page(
            [
                heading("DMS - %s (%i pages)" % (original_name, page_count(original_name))),
                """
                <div id=edit>
                <form class=description method=POST>
                  <textarea class=input name="value" placeholder="Title and description">%s</textarea>
                  <input class=button type="submit" value="Save">
                </form>%s<img class=preview src="%s"></div>"""
                % (
                    cgi.html.escape(data, quote=True),
                    link_list(
                        [
                            link_item("View Original version", "download", original_name + ".orig.pdf"),
                            link_item("View OCR version", "download", original_name + ".pdf"),
                        ]
                    ),
                    url_for("download", name=original_name + ".png"),
                ),
            ]
        )
    else:
        open(description_file, "w").write(query)
        return redirect(url_for("root"))


@app.route("/download/<name>")
def download(name):
    return send_from_directory(DATA_DIR, name)


@app.route("/")
def root():
    query = request.args.get("q", "")
    filter_to = set(search(query))
    return render_page(
        [
            heading(("DMS - '%s'" % (query,)) if query else "DMS"),
            search_box(query),
            list_of_directories(
                lambda filename: '<a href="%s"><img title="%i pages" class="small %s" src="%s"></a>'
                                 % (
                                     url_for("edit", name=filename),
                                     page_count(filename),
                                     compute_img_class(filename),
                                     url_for("download", name=filename + ".png"),
                                 ),
                filter_to=filter_to,
            ),
        ]
    )
