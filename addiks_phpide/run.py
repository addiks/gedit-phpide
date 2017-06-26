#!/usr/bin/python

# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-phpide
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from .PHP.PhpIndex import PhpIndex
from .update_gtk import update_gtk

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
