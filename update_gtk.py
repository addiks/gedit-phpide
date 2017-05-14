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

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk
from PHP.PhpIndex import PhpIndex
from _thread import start_new_thread
import sys, os

def __prepare_gtk_process_window(index_filepath, folder_path, windowTitle, indexPathManager=None):

    processWindow = Gtk.Window(title=windowTitle)
    processWindow.set_default_size(500, 25)
    processWindow.connect("delete-event", Gtk.main_quit)
    processWindow.set_border_width(10)

    processBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    processWindow.add(processBox)

    processBar = Gtk.ProgressBar(margin=5)
    processBarBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    processBarBox.set_size_request(-1, 32)
    processBarBox.pack_start(processBar, True, True, 0)
    processBox.pack_start(processBarBox, True, True, 0)

    processLabel = Gtk.Label()
    processLabel.set_halign(Gtk.Align.START)
    processLabel.set_text("Initiating... (should only take seconds)")
    processBox.pack_start(processLabel, True, True, 0)

    processWindow.show_all()

    def update_callback(done_count, all_count, file_path):
        if len(file_path) > 96:
            file_path = file_path[0:36] + "... ..." + file_path[-36:]
        message = "("+str(done_count)+"/"+str(all_count)+") " + file_path
        Gdk.threads_enter()
        processBar.set_fraction(float(done_count) / all_count)
        processLabel.set_text(message)
        processLabel.queue_draw()
        Gdk.threads_leave()

    def error_callback(message):
        Gdk.threads_enter()
        sys.stderr.write(message)
        processLabel.set_text(message)
        processLabel.queue_draw()
        Gdk.threads_leave()

    def finished_callback():
        Gdk.threads_enter()
        processBar.set_fraction(1)
        processLabel.set_text("Process finished. You may close this window now.")
        processLabel.queue_draw()
        Gdk.threads_leave()

    Gdk.threads_init()

    index = PhpIndex(index_filepath, update_callback, error_callback, finished_callback, indexPathManager)
    return index

def update_gtk(index_filepath, folder_path, indexPathManager=None):
    index = __prepare_gtk_process_window(index_filepath, folder_path, "Updating PHP-Index...", indexPathManager)
    start_new_thread(index.update, (folder_path, ))

def build_gtk(index_filepath, folder_path, indexPathManager=None):
    index = __prepare_gtk_process_window(index_filepath, folder_path, "Rebuilding PHP-Index...", indexPathManager)
    start_new_thread(index.build, (folder_path, ))
