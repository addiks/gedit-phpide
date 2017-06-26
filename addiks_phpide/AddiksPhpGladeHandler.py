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

from gi.repository import GLib, Gtk, Gdk
from os.path import expanduser
import traceback
import re
import os
import subprocess
from subprocess import Popen, PIPE
from _thread import start_new_thread

from .PHP.functions import get_namespace_by_classname
from .PHP.GraphMLExporter import GraphMLExporter

class AddiksPhpGladeHandler:

    def __init__(self, plugin, builder):
        self._plugin  = plugin
        self._builder = builder

    def __get_results_by_search_text(self, searchText):
        searchText = searchText.strip()

        searchTerms = re.split('\s+', searchText)

        smallestLen = None
        for term in searchTerms:
            if smallestLen == None or len(term) < smallestLen:
                smallestLen = len(term)

        results = []
        if len(searchTerms)>0 and smallestLen>2:
            index = self._plugin.get_index_storage()
            results = index.do_fulltext_search(searchTerms)

        return results

    ### SEARCH INDEX

    def onIndexSearchChanged(self, searchEntry, userData=None):
        searchText = searchEntry.get_text()
        results = self.__get_results_by_search_text(searchText)

        listStore = self._builder.get_object('liststoreSearchIndex')
        listStore.clear()

        if len(results)>0:
            # TODO: update priorities by context

            results.sort(key=self._sortKeyForAutocomplete)

            index = 1
            for filePath, line, column, typeName, title in results:
                rowIter = listStore.append()
                listStore.set_value(rowIter, 0, filePath)
                listStore.set_value(rowIter, 1, line)
                listStore.set_value(rowIter, 2, column)
                listStore.set_value(rowIter, 3, title)
                listStore.set_value(rowIter, 4, index)
                listStore.set_value(rowIter, 5, typeName)
                index += 1

    def _sortKeyForAutocomplete(self, result):
        key = ""
        filePath, line, column, typeName, title = result

        if typeName == "Class":
            namespace, className = get_namespace_by_classname(title)
            key = self.__sortKey(className) + self.__sortKey(namespace)
        else:
            key = self.__sortKey(title)

        return key

    def __sortKey(self, name):
        if name != None:
            length = len(name)
            length = str(length).zfill(4)
            return length + name
        return ""

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

    ### CALLER WINDOW

    def onCallerRowActivated(self, treeView, treePath, treeViewColumn, userData=None):
        listStore = self._builder.get_object('liststoreCallers')

        rowIter = listStore.get_iter(treePath)

        filePath = listStore.get_value(rowIter, 0)
        line     = listStore.get_value(rowIter, 1)

        self._plugin.open_by_position(filePath, line, 1)

    ### EXPORT TO GRAPH ML

    def onExportGraphMLWindowShown(self, window, userData=None):
        plugin = self._plugin

        executionPatternEntry = self._builder.get_object('entryGraphMLExecutionPattern')

        treeViewAvailable = self._builder.get_object('treeviewExportGraphMLAvailable')
        treeViewSelected  = self._builder.get_object('treeviewExportGraphMLSelected')
        treeViewExcluded  = self._builder.get_object('treeviewExportGraphMLExcluded')

        treeViewAvailable.connect("drag-data-get", self.onTreeViewAvailableDragDataGet)
        treeViewAvailable.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            [],
            Gdk.DragAction.COPY
        )
        treeViewAvailable.drag_source_add_text_targets()

        treeViewSelected.connect("drag-data-received", self.onTreeViewSelectedDragDataReceived)
        treeViewSelected.enable_model_drag_dest(
            [],
            Gdk.DragAction.COPY
        )
        treeViewSelected.drag_dest_add_text_targets()

        treeViewExcluded.connect("drag-data-received", self.onTreeViewSelectedDragDataReceived)
        treeViewExcluded.enable_model_drag_dest(
            [],
            Gdk.DragAction.COPY
        )
        treeViewExcluded.drag_dest_add_text_targets()

        settings = plugin.get_settings()

        commandPattern = settings.get_string("graphml-execute-pattern")

        executionPatternEntry.set_text(commandPattern)

    def onTreeViewAvailableDragDataGet(self, treeView, dragContext, data, info, time):
        selection = treeView.get_selection()
        store, selected_rows = selection.get_selected_rows()
        listStore = treeView.get_model()

        for path in selected_rows:
            treeIter  = listStore.get_iter(path)
            classname = listStore.get_value(treeIter, 0)
            data.set_text(classname, -1)

    def onTreeViewSelectedDragDataReceived(self, treeView, dragContext, x, y, data, info, time):
        classname = data.get_text()
        liststore = treeView.get_model()
        rowIterSelected = liststore.append()
        liststore.set_value(rowIterSelected, 0, classname)

    def onExportGraphMLAvailableChanged(self, searchEntry, userData=None):
        searchText = searchEntry.get_text()
        results = self.__get_results_by_search_text(searchText)

        listStore = self._builder.get_object('liststoreExportGraphMLAvailable')
        listStore.clear()

        if len(results)>0:
            # TODO: update priorities by context

            results.sort(key=self._sortKeyForAutocomplete)

            for filePath, line, column, typeName, title in results:
                if typeName == 'Class':
                    rowIter = listStore.append()
                    listStore.set_value(rowIter, 0, title)

    def onExportGraphMLAvailableRowActivated(self, treeView, treePath, treeViewColumn, userData=None):
        listStoreAvailable = self._builder.get_object('liststoreExportGraphMLAvailable')
        listStoreSelected  = self._builder.get_object('liststoreExportGraphMLSelected')

        rowIterAvailable = listStoreAvailable.get_iter(treePath)

        classname = listStoreAvailable.get_value(rowIterAvailable, 0)

        rowIterSelected = listStoreSelected.append()
        listStoreSelected.set_value(rowIterSelected, 0, classname)

    def onExportGraphMLRowActivatedRemove(self, treeView, treePath, treeViewColumn, userData=None):
        listStore = treeView.get_model()

        rowIter = listStore.get_iter(treePath)
        listStore.remove(rowIter)

    def onExportGraphMLExecute(self, button, userData=None):
        listStoreSelected = self._builder.get_object('liststoreExportGraphMLSelected')
        listStoreExcluded = self._builder.get_object('liststoreExportGraphMLExcluded')
        depthAdjustment = self._builder.get_object('adjustmentExportGraphMLDepth')

        depth = int(depthAdjustment.get_value())

        counter = 0
        while True:
            filePath = "/tmp/addiks.phpide." + str(counter) + ".graphml"
            if not os.path.exists(filePath):
                break
            counter += 1

        classesSelected = []
        for modelRow in listStoreSelected:
            rowIter = modelRow.iter
            classesSelected.append(listStoreSelected.get_value(rowIter, 0))

        classesExcluded = []
        for modelRow in listStoreExcluded:
            rowIter = modelRow.iter
            classesExcluded.append(listStoreExcluded.get_value(rowIter, 0))

        optionObjectMap = [
            ("contain_methods", "checkbuttonGraphMLContainMethods"),
            ("contain_members", "checkbuttonGraphMLContainMembers"),
            ("include_parental_inheritance", "checkbuttonGraphMLIncludeParentalInheritanceRelations"),
            ("include_children_inheritance", "checkbuttonGraphMLIncludeChildrenInheritanceRelations"),
            ("include_interfaces", "checkbuttonGraphMLIncludeInterfaceRelations"),
            ("include_has_a_composition", "checkbuttonGraphMLIncludeHasACompositionRelations"),
            ("include_is_part_of_composition", "checkbuttonGraphMLIncludeIsPartOfCompositionRelations"),
            ("include_uses_references", "checkbuttonGraphMLIncludeUsesRelations"),
            ("include_usedby_references", "checkbuttonGraphMLIncludeUsedByRelations"),
        ]

        options = {}

        for optionKey, objectId in optionObjectMap:
            options[optionKey] = self._builder.get_object(objectId).get_active()

        start_new_thread(self._do_ExportGraphMLExecute, (classesSelected, classesExcluded, filePath, depth, options))

    def _do_ExportGraphMLExecute(self, classesSelected, classesExcluded, filePath, depth, options={}):
        plugin = self._plugin
        storage = plugin.create_index_storage()

        executionPatternEntry = self._builder.get_object('entryGraphMLExecutionPattern')

        exporter = GraphMLExporter()
        exporter.exportClassGraphhToFile(
            plugin,
            storage,
            classesSelected,
            filePath,
            depth,
            classesExcluded,
            options
        )

        commandPattern = executionPatternEntry.get_text()
        commandLine = commandPattern % filePath
        commandLine = commandLine.split(" ")

        command = []
        for commandPart in commandLine:
            commandPart = os.path.expanduser(commandPart)
            command.append(commandPart)

        sp = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        sp.wait()
