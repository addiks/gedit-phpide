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

from gi.repository import GLib, Gtk, GObject, Gedit, PeasGtk, Gio, GtkSource
from PHP.PhpFile import PhpFile
from PHP.get_namespace_by_classname import get_namespace_by_classname
from PHP.IndexPathManager import IndexPathManager
from update_gtk import update_gtk, build_gtk
from AddiksPhpGladeHandler import AddiksPhpGladeHandler
from AddiksPhpIndex import AddiksPhpIndex
from inspect import getmodule
from _thread import start_new_thread
import os
import random
import time
import subprocess

class AddiksPhpIndexWindow(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self.__phpfiles = {}
        self.__is_outline_active = False
        self._storage = None
        self._glade_builder = None
        self._glade_handler = None

    def do_activate(self):
        AddiksPhpIndex.get().register_window(self)

        plugin_path = os.path.dirname(__file__)
        self._ui_manager = self.window.get_ui_manager()
        actions = [
            ['BuildIndexAction',        "Build index",          "",   self.on_build_index],
            ['UpdateIndexAction',       "Update index",         "",   self.on_update_index],
            ['ToggleOutlineAction',     "Toogle outline",       "F2", self.on_toggle_outline],
            ['OpenDeclarationAction',   "Open declaration",     "F3", self.on_open_declaration_view],
            ['OpenTypeViewAction',      "Open type view",       "F4", self.on_open_type_view],
            ['SearchIndexAction',       "Search the index",     "<Ctrl>L",   self.on_search_index],
            ['OpenCallViewAction',      "Open call view",       "",   self.on_open_call_view],
            ['OpenDepencyViewAction',   "Open depency view",    "",   self.on_open_depency_view],
            ['ManageIndexPathsAction',  "Manage index paths",   "",   self.on_index_paths_manager],
            ['PhpAction',               "PHP",                  "",   None],
        ]

        self._actions = Gtk.ActionGroup("AddiksPhpMenuActions")
        for actionName, title, shortcut, callback in actions:
            self._actions.add_actions([(actionName, Gtk.STOCK_INFO, title, shortcut, "", callback),])

        with open(plugin_path + "/menubar.xml", "r", encoding = "ISO-8859-1") as f:
            menubarXml = f.read()

        self._ui_manager.insert_action_group(self._actions)
        self._ui_merge_id = self._ui_manager.add_ui_from_string(menubarXml)
        self._ui_manager.ensure_update()

    def do_deactivate(self):
        AddiksPhpIndex.get().unregister_window(self)

    def do_update_state(self):
        document = self.window.get_active_document()

        if document != None and document.get_location() != None:
            path = document.get_location().get_path()
            if path[-4:] != '.php' and path[-6:] != '.phtml':
                self._ui_manager.remove_ui(self._ui_merge_id)

    ### HELPERS

    def get_index_storage(self):
        if self._storage == None:
            indexPath = self.get_index_filepath()

            if indexPath == None:
                pass

            elif indexPath == 'neo4j':
                from storage.neo4j import Neo4jStorage
                self._storage = Neo4jStorage()

            elif indexPath == 'dummy':
                from storage.dummy import DummyStorage
                self._storage = DummyStorage()

            elif indexPath.find(".sqlite3")>0:
                from storage.sqlite3 import Sqlite3Storage
                self._storage = Sqlite3Storage(indexPath)

            elif indexPath.find("/")>0:
                from storage.shelve import ShelveStorage
                self._storage = ShelveStorage(indexPath)

            else:
                raise Exception("Cannot open index '"+indexPath+"'!")

        return self._storage

    def get_php_fileindex(self, filePath=None):
        isLocalFile = False
        if filePath == None:
            document = self.window.get_active_document()
            if document != None and document.get_location() != None:
                filePath = document.get_location().get_path()
                filePath = os.path.abspath(filePath)
                isLocalFile = True
        if filePath not in self.__phpfiles:
            if isLocalFile:
                start, end = document.get_bounds()
                code = document.get_text(start, end, False)
            else:
                with open(filePath, "r", encoding = "ISO-8859-1") as f:
                    code = f.read()
            self.__phpfiles[filePath] = PhpFile(code, self, self.get_index_storage())
        return self.__phpfiles[filePath]

    def invalidate_php_fileindex(self, filePath=None):
        if filePath == None:
            document = self.window.get_active_document()
            if document != None and document.get_location() != None:
                filePath = document.get_location().get_path()
                filePath = os.path.abspath(filePath)
        if filePath in self.__phpfiles:
            del self.__phpfiles[filePath]

    def get_git_directory(self):
        document = self.window.get_active_document()
        if document != None and document.get_location() != None:
            filepath = document.get_location().get_path()
            filepath = os.path.abspath(filepath)
            while filepath != "/":
                filepath = os.path.dirname(filepath)
                if os.path.exists(filepath + "/.git"):
                    return filepath
        else:
            return None

    def get_index_filepath(self):
        gitpath = self.get_git_directory()
        if(gitpath != None):
            return gitpath + "/.git/addiks.phpindex.sqlite3"

    def is_index_built(self):
        filepath = self.get_index_filepath()
        if(os.path.exists(filepath)):
            return True
        return False

    def on_index_not_build(self):
        dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, "Build index first!")
        dialog.format_secondary_text("To perform this action, you first need to build the index for this working directory.")
        dialog.run()
        return False

    def on_index_calls(self, current, count):
        print(current + "/" + count)

    def get_current_cursor_position(self):
        line = None
        column = None
        document = self.window.get_active_document()
        if document != None and document.get_location() != None:

            insertMark = document.get_insert()
            insertIter = document.get_iter_at_mark(insertMark)
            line   = insertIter.get_line()+1
            column = insertIter.get_line_index()+1
        return (line, column, )

    def get_class_hierarchy(self, className):
        storage = self.get_index_storage()
        hierarchy = {className: self.get_class_children_recursive(className)}
        parentClass = className
        while True:
            namespace, parentClass = get_namespace_by_classname(parentClass)
            parentClass = storage.get_class_parent(namespace, parentClass)
            if parentClass != None:
                hierarchy = {parentClass: hierarchy}
            else:
                break
        return hierarchy

    def get_class_children_recursive(self, className):
        storage = self.get_index_storage()
        childHierarchy = {}
        for childClassName in storage.get_class_children(className):
            childHierarchy[childClassName] = self.get_class_children_recursive(childClassName)
        return childHierarchy

    def open_by_position(self, filePath, line, column):
        GLib.idle_add(self.do_open_by_position, filePath, line, column)

    def do_open_by_position(self, filePath, line, column):
        if filePath != None:
            document = self.window.get_active_document()
            if filePath == os.path.abspath(document.get_location().get_path()):
                view = self.window.get_active_view()
                insertMark = document.get_insert()
                insertIter = document.get_iter_at_mark(insertMark)
                insertIter.set_line(line-1)
                insertIter.set_line_index(column-1)
                document.place_cursor(insertIter)
                view.scroll_to_iter(insertIter, 0.0, True, 0.0, 0.0)

            else:
                start_new_thread(subprocess.call, (['gedit', filePath, "+"+str(line)+":"+str(column)], ))

    ### INDEX PATH MANAGER

    __indexPathManager = None

    def get_index_path_manager(self):
        if self.__indexPathManager is None:
            gitpath = self.get_git_directory()
            if(gitpath != None):
                csvFilePath = gitpath + "/.git/addiks.excludes.csv"
                self.__indexPathManager = IndexPathManager(csvFilePath)
        return self.__indexPathManager

    ### GLADE

    def getGladeHandler(self):
        if self._glade_handler == None:
            self.__initGlade()
        return self._glade_handler

    def getGladeBuilder(self):
        if self._glade_builder == None:
            self.__initGlade()
        return self._glade_builder

    def __initGlade(self):
        self._glade_builder = Gtk.Builder()
        self._glade_builder.add_from_file(os.path.dirname(__file__)+"/phpide.glade")
        self._glade_handler = AddiksPhpGladeHandler(self, self._glade_builder)
        self._glade_builder.connect_signals(self._glade_handler)

    ### MENU EVENTS

    def on_index_paths_manager(self, action, data=None):
        if self.get_index_path_manager() != None:
            window = self.getGladeBuilder().get_object("windowIndexPathsManager")
            window.show_all()
        else:
            dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, "Not a git project!")
            dialog.format_secondary_text("The index-include/-exclude path'scan only be configured for files in a git workspace.")
            dialog.run()

    def on_build_index(self, action, data=None):
        document = self.window.get_active_document()
        if document != None and document.get_location() != None:
            indexPath = self.get_index_filepath()
            gitPath   = self.get_git_directory()
            pathManager = self.get_index_path_manager()
            build_gtk(indexPath, gitPath, pathManager)

    def on_update_index(self, action, data=None):
        document = self.window.get_active_document()
        if document != None and document.get_location() != None:
            indexPath = self.get_index_filepath()
            gitPath   = self.get_git_directory()
            pathManager = self.get_index_path_manager()
            update_gtk(indexPath, gitPath, pathManager)

    def on_open_declaration_view(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()
        line, column = self.get_current_cursor_position()
        if line != None and column != None:
            filePath, line, column = self.get_php_fileindex().get_declared_position_by_position(line, column)
            self.open_by_position(filePath, line, column)

    def on_search_index(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()
        gladeBuilder = self.getGladeBuilder()
        window = gladeBuilder.get_object("windowSearchIndex")
        window.connect('delete-event', lambda w, e: w.hide() or True)
        window.show_all()

    def on_open_type_view(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()

        line, column = self.get_current_cursor_position()
        if line != None and column != None:
            declarationType, name, containingClassName = self.get_php_fileindex().get_declaration_by_position(line, column)
            namespace = self.get_php_fileindex().get_namespace()

            if declarationType == 'class':
                className = name

            elif containingClassName != None:
                className = containingClassName

            if className[0] != '\\':
                className = namespace + '\\' + className

            hierarchy = self.get_class_hierarchy(className)
            if hierarchy != None:

                # create treestore from hierarchy
                treeStore = Gtk.TreeStore(str)
                className = list(hierarchy)[0]
                hierarchy = hierarchy[className]
                self.__type_view_treestore_add_row(treeStore, None, className, hierarchy)

                treeView = Gtk.TreeView(model=treeStore)
                treeView.set_headers_visible(False)
                treeView.append_column(Gtk.TreeViewColumn("class", Gtk.CellRendererText(), text=0))
                treeView.expand_all()
                treeView.connect("row-activated", self.__on_typeview_row_activated)

                scrolledWindow = Gtk.ScrolledWindow()
                scrolledWindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                scrolledWindow.add(treeView)

                window = Gtk.Window(title="Typeview of "+className)
                window.set_default_size(50, 250)
                window.add(scrolledWindow)
                window.show_all()

    def __on_typeview_row_activated(self, treeView, path, column, userData=None):
        storage = self.get_index_storage()
        treeStore = treeView.get_model()
        className, = treeStore.get(treeStore.get_iter(path), 0)
        namespace, className = get_namespace_by_classname(className)
        filePath, line, column = storage.get_class_position(namespace, className)
        self.open_by_position(filePath, line, column)

    def __type_view_treestore_add_row(self, treeStore, parentTreeIter, className, hierarchy):
        treeIter = treeStore.append(parentTreeIter, [className])
        for childClassName in hierarchy:
            self.__type_view_treestore_add_row(treeStore, treeIter, childClassName, hierarchy[childClassName])

    def on_toggle_outline(self, action, data=None):
        index = self.get_php_fileindex()
        document = self.window.get_active_document()
        if document != None and document.get_location() != None:
            beforeIter = document.get_iter_at_mark(document.get_insert())
            beforeMark = document.create_mark("outline-before", beforeIter, True)

            tagTable = document.get_tag_table()
            tag = tagTable.lookup("invisible")
            if tag == None:
                tag = document.create_tag('invisible', invisible=True)

            tokens = index.get_tokens()
            self.__is_outline_active = self.__is_outline_active == False
            if self.__is_outline_active:

                outlineLines = []
                for block in index.get_blocks():
                    if len(block)>2:
                        outlineLines.append(tokens[block[3]][2])
                        if block[2] == 'class':
                            for memberIndex in block[10]:
                                outlineLines.append(tokens[memberIndex][2])
                            for constIndex in block[11]:
                                outlineLines.append(tokens[constIndex][2])
                outlineLines = list(set(outlineLines))
                outlineLines.sort()
                outlineLines.append(0)

                beginIter = document.get_iter_at_mark(document.get_insert())
                beginIter.set_line_offset(0)
                endIter = beginIter.copy()
                endIter.set_line_offset(0)
                beforeLine = 0
                for line in outlineLines:
                    beginIter.set_line(beforeLine)
                    endIter.set_line(line-1)
                    beforeLine = line
                    document.apply_tag(tag, beginIter, endIter)
            else:
                beginIter = document.get_iter_at_mark(document.get_insert())
                beginIter.set_line(0)
                endIter = beginIter.copy()
                endIter.set_line(-1)
                document.remove_tag(tag, beginIter, endIter)

            view = self.window.get_active_view()
            view.scroll_to_mark(beforeMark, 0.0, True, 0.0, 0.0)

    def on_open_call_view(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()

        line, column = self.get_current_cursor_position()
        if line != None and column != None:
            use_statements = self.get_php_fileindex().get_use_statements()
            declarationType, name, containingClassName = self.get_php_fileindex().get_declaration_by_position(line, column)
            namespace = self.get_php_fileindex().get_namespace()

            storage = self.get_index_storage()

            uses = None
            if declarationType == 'method':
                uses = storage.get_method_uses(name)

            elif declarationType == 'function':
                uses = storage.get_function_uses(name)

            elif declarationType == 'member':
                uses = storage.get_member_uses(name)

            elif declarationType == 'class':
                if name in use_statements:
                    name = use_statements[name]
                elif name[0] != '\\':
                    name = namespace + '\\' + name
                uses = storage.get_class_uses(name)

            elif declarationType == 'constant':
                uses = storage.get_constant_uses(name)

            else:
                return

            builder = self.getGladeBuilder()
            listStore = builder.get_object('liststoreCallers')

            filteredUses = {}
            for filePath, line, column, className, functionName in uses:
                filteredUses[filePath + ":" + str(line)] = [filePath, line, column, className, functionName]
            filteredUses = list(filteredUses.values())
            filteredUses.sort(key=self.__filteredUsesKey)

            listStore.clear()
            for filePath, line, column, className, functionName in filteredUses:
                preview = ""
                if os.path.exists(filePath):
                    with open(filePath, "r", encoding = "ISO-8859-1") as f:
                        code = f.read()
                    lines = code.split("\n")
                    preview = lines[line-1]
                rowIter = listStore.append()
                listStore.set_value(rowIter, 0, filePath)
                listStore.set_value(rowIter, 1, line)
                listStore.set_value(rowIter, 2, className)
                listStore.set_value(rowIter, 3, functionName)
                listStore.set_value(rowIter, 4, preview)

            window = builder.get_object('windowCallers')
            window.connect('delete-event', lambda w, e: w.hide() or True)
            window.show_all()

    def __filteredUsesKey(self, use):
        return use[3] + str(use[1]) + use[4]

    def on_open_depency_view(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()
        print("Open depency-view")

