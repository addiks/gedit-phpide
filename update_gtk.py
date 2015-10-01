#!/usr/bin/python

from gi.repository import Gtk, Gdk
from phpindex import PhpIndex
from _thread import start_new_thread
import sys, os

def __prepare_gtk_process_window(index_filepath, folder_path, windowTitle):

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

    index = PhpIndex(index_filepath, update_callback, error_callback, finished_callback)
    return index

def update_gtk(index_filepath, folder_path):
    index = __prepare_gtk_process_window(index_filepath, folder_path, "Updating PHP-Index...")
    start_new_thread(index.update, (folder_path, ))

def build_gtk(index_filepath, folder_path):
    index = __prepare_gtk_process_window(index_filepath, folder_path, "Rebuilding PHP-Index...")
    start_new_thread(index.build, (folder_path, ))

