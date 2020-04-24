(tiny) Document Management System
=================================

This is a simple document management system which can search in documents and render previews.
It also allows tagging.

To install:

  1. `git clone https://github.com/xoraxax/dms`
  2. `cd dms`
  3. `mkdir db`
  4. `virtualenv -p python3 env`
  5. `. env/bin/activate`
  6. `pip install flask`
  7. `sudo apt install pdfsandwich poppler-utils imagemagick`

To run:

  1. Ensure you are in the `dms` folder.
  2. `sh run.sh`
