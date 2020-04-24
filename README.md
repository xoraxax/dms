(tiny) Document Management System
=================================

This is a simple document management system which can search in documents and render previews.
It also allows tagging.

To install:

  1. `git clone https://github.com/xoraxax/dms`
  2. `cd dms`
  3. `mkdir db`
  4. `mkdir ~/source_folder; ln -s ~/source_folder ./SOURCE_DIR`
  5. `virtualenv -p python3 env`
  6. `. env/bin/activate`
  7. `pip install flask`
  8. `sudo apt install pdfsandwich poppler-utils imagemagick`

To run:

  1. Ensure you are in the `dms` folder.
  2. `sh run.sh`

Now copy PDF files into `~/source_folder` and watch them appear slightly later in your browser at
`http://localhost:5000/`.
