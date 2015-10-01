#!/usr/bin/python

import sys
from phpindex import PhpIndex
from update_gtk import update_gtk

def update_callback(done_count, all_count, file_path):
    progressStr = str(done_count) + "/" + str(all_count) + " : "
    print(progressStr + file_path)

def error_callback(message):
    sys.stderr.write(message)

if len(sys.argv)<4:
    print(" USAGE: "+sys.argv[0]+" [build|update|update-gtk] [INDEX-FILEPATH] [FOLDER-PATH]")

elif sys.argv[1] == 'build':
    index = PhpIndex(sys.argv[2], update_callback, error_callback)
    index.build(sys.argv[3])

elif sys.argv[1] == 'update':
    index = PhpIndex(sys.argv[2], update_callback, error_callback)
    index.update(sys.argv[3])

elif sys.argv[1] == 'update-gtk':
    from gi.repository import Gtk
    index_filepath = sys.argv[1]
    folder_path    = sys.argv[2]
    update_gtk(index_filepath, folder_path)
    Gtk.main()
