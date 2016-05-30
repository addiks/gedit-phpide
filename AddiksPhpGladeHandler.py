# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-window-management
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

from gi.repository import GLib, Gtk, Gdk
from os.path import expanduser
import traceback
import re

class AddiksPhpGladeHandler:

    def __init__(self, plugin, builder):
        self._plugin  = plugin
        self._builder = builder

    ### SEARCH INDEX

    def onIndexSearchChanged(self, searchEntry, userData=None):
        searchText = searchEntry.get_text()
        searchText = searchText.strip()

        searchTerms = re.split('\s+', searchText)

        listStore = self._builder.get_object('liststoreSearchIndex')
        listStore.clear()

        smallestLen = None
        for term in searchTerms:
            if smallestLen == None or len(term) < smallestLen:
                smallestLen = len(term)

        if len(searchTerms)>0 and smallestLen>2:
            index = self._plugin.get_index_storage()
            results = index.do_fulltext_search(searchTerms)

            # TODO: update priorities by context

            results = sorted(results, key=lambda a: a[3], reverse=True) # sort by priority

            index = 1
            for filePath, line, column, priority, typeName, title in results:
                if priority < 0:
                    priority = 0
                rowIter = listStore.append()
                listStore.set_value(rowIter, 0, filePath)
                listStore.set_value(rowIter, 1, line)
                listStore.set_value(rowIter, 2, column)
                listStore.set_value(rowIter, 3, title)
                listStore.set_value(rowIter, 4, index)
                listStore.set_value(rowIter, 5, typeName)
                listStore.set_value(rowIter, 6, priority)
                index += 1

    def onSearchIndexRowActivated(self, treeView, treePath, treeViewColumn, userData=None):

        window    = self._builder.get_object("windowSearchIndex")
        listStore = self._builder.get_object('liststoreSearchIndex')

        rowIter = listStore.get_iter(treePath)

        filePath = listStore.get_value(rowIter, 0)
        line     = listStore.get_value(rowIter, 1)
        column   = listStore.get_value(rowIter, 2)

        window.hide()

        self._plugin.open_by_position(filePath, line, column)

    ### INDEX PATHS MANAGER

    __indexManagerPathToRowIter = {}

    def onIndexPathsManagerShow(self, treePath=None, userData=None):
        indexPathManager = self._plugin.get_index_path_manager()
        listStore = self._builder.get_object('liststoreIndexPathsManager')

        listStore.clear()
        self.__indexManagerPathToRowIter = {}
        for path, isExclude in indexPathManager.getPaths():
            rowIter = listStore.append()
            listStore.set_value(rowIter, 0, path)
            listStore.set_value(rowIter, 1, isExclude)
            self.__indexManagerPathToRowIter[path] = rowIter

    def onIndexPathsManagerAddPath(self, button, userData=None):
        indexPathManager = self._plugin.get_index_path_manager()
        listStore = self._builder.get_object('liststoreIndexPathsManager')

        dialog = self._builder.get_object('dialogIndexPathManager')
        fileChooser = self._builder.get_object('filechooserbuttonIndexPathManager')
        radiobuttonExclude = self._builder.get_object('radiobuttonIndexPathManagerExclude')

        response = dialog.run()
        dialog.hide()

        if response == Gtk.ResponseType.OK:
            entryPath = fileChooser.get_filename()
            isExclude = radiobuttonExclude.get_active()

            indexPathManager.addPath(entryPath, isExclude)
            self.onIndexPathsManagerShow()

    def onIndexPathsManagerRemovePath(self, button, userData=None):
        indexPathManager = self._plugin.get_index_path_manager()
        treeView = self._builder.get_object('treeviewIndexPathsManager')
        listStore = self._builder.get_object('liststoreIndexPathsManager')

        selection = treeView.get_selection()
        store, selected_rows = selection.get_selected_rows()

        for path in selected_rows:
            treeIter  = listStore.get_iter(path)
            entryPath = listStore.get_value(treeIter, 0)
            indexPathManager.removePath(entryPath)
            self.onIndexPathsManagerShow()

    def onIndexPathsManagerEditPath(self, button, userData=None):
        indexPathManager = self._plugin.get_index_path_manager()
        treeView = self._builder.get_object('treeviewIndexPathsManager')
        listStore = self._builder.get_object('liststoreIndexPathsManager')

        dialog = self._builder.get_object('dialogIndexPathManager')
        fileChooser = self._builder.get_object('filechooserbuttonIndexPathManager')
        radiobuttonExclude = self._builder.get_object('radiobuttonIndexPathManagerExclude')

        selection = treeView.get_selection()

        store, selected_rows = selection.get_selected_rows()

        for path in selected_rows:
            treeIter  = listStore.get_iter(path)
            entryPath = listStore.get_value(treeIter, 0)
            isExclude = listStore.get_value(treeIter, 1)

            fileChooser.set_filename(entryPath)
            radiobuttonExclude.set_active(isExclude)

            response = dialog.run()
            dialog.hide()

            newEntryPath = fileChooser.get_filename()
            isExclude = radiobuttonExclude.get_active()

            if response == Gtk.ResponseType.OK:
                indexPathManager.modifyPath(entryPath, newEntryPath, isExclude)
                self.onIndexPathsManagerShow()

