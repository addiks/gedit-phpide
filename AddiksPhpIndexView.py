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

from PHP.get_namespace_by_classname import get_namespace_by_classname
from PHP.PhpFileAnalyzer import PhpFileAnalyzer
from PHP.PhpIndex import PhpIndex
from PHP.IndexPathManager import IndexPathManager
from PHP.phplexer import token_num

from AutocompleteProvider import AutocompleteProvider
from AddiksPhpIndexApp import AddiksPhpIndexApp
from AddiksPhpGladeHandler import AddiksPhpGladeHandler
from update_gtk import update_gtk, build_gtk

from inspect import getmodule
from _thread import start_new_thread

import os
import random
import time
import subprocess

T_COMMENT     = token_num("T_COMMENT")
T_DOC_COMMENT = token_num("T_DOC_COMMENT")
T_VARIABLE    = token_num("T_VARIABLE")

class AddiksPhpIndexView(GObject.Object, Gedit.ViewActivatable):
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)
        self.__completion_provider = None
        self.__phpfiles = {}
        self.__is_outline_active = False
        self._storage = None
        self._glade_builder = None
        self._glade_handler = None

    def do_activate(self):
        AddiksPhpIndexApp.get().register_view(self)

        completion = self.view.get_completion()
        provider = self.get_completion_provider()
        if provider not in completion.get_providers():
            completion.add_provider(provider)

        document = self.view.get_buffer()
        document.connect("changed", self.__on_document_changed)
        document.connect("insert-text", self.__on_document_insert)
        document.connect("saved", self.__on_document_saved)

    def do_deactivate(self):
        AddiksPhpIndexApp.get().unregister_view(self)

    def do_update_state(self):
        pass

    def __on_document_insert(self, document, textIter, insertedText, length, userData=None):
        if document.get_location() != None:

            # adding a semicolon could mean the user finished writing a statement. maybe we can auto-add something.
            if insertedText == ';':
                code = document.get_text(document.get_start_iter(), document.get_end_iter(), True)
                analyzer = PhpFileAnalyzer(code, self, self.get_index_storage())
                tokens = analyzer.get_tokens()
                tokenIndex = analyzer.get_token_index_by_position(textIter.get_line()+1, textIter.get_line_offset()+1)

                declarationType, declaredName, className = analyzer.get_declaration_by_token_index(tokenIndex)

                if declarationType == 'member' and tokens[tokenIndex][1] == declaredName:
                    # finished a member, we can auto-add a doc-comment for that
                    line = tokens[tokenIndex][2]
                    lineBeginIter = document.get_iter_at_line_index(line-1, 0)

                    tokenIndexComment = analyzer.get_token_index_by_position(line, 0)
                    if tokens[tokenIndexComment][0] not in [T_COMMENT, T_DOC_COMMENT]:
                        codeLine = document.get_text(
                            lineBeginIter,
                            document.get_iter_at_line_index(line, 0),
                            True
                        )

                        indention = ""
                        while codeLine[len(indention)] in [" ", "\t", "*"]:
                            indention += codeLine[len(indention)]

                        commentCode  = indention + "/**\n"
                        commentCode += indention + " * @var mixed\n"
                        commentCode += indention + " */\n"
                        GLib.idle_add(self.do_textbuffer_insert, document, line-1, 0, commentCode)

            # adding an equal sign could mean the user is writing a new variable. maybe we can add a doc-comment.
            if insertedText == '=':
                code = document.get_text(document.get_start_iter(), document.get_end_iter(), True)
                analyzer = PhpFileAnalyzer(code, self, self.get_index_storage())
                tokens = analyzer.get_tokens()
                tokenIndex = analyzer.get_token_index_by_position(textIter.get_line()+1, textIter.get_line_offset()+1)

                if tokens[tokenIndex][0] == T_VARIABLE and tokens[tokenIndex-1][1] in [';', '{']:
                    methodBlock = analyzer.get_method_block_is_in(tokenIndex)
                    if methodBlock != None:
                        variableName = tokens[tokenIndex][1]

                        isFirstUsage = True
                        for token in tokens[methodBlock[0]:tokenIndex]:
                            if tokens[0] == T_VARIABLE and token[1] == variableName:
                                isFirstUsage = False
                                break

                        if isFirstUsage:
                            # added a new variable, we can auto-add a doc-comment for that
                            line = tokens[tokenIndex][2]
                            lineBeginIter = document.get_iter_at_line_index(line-1, 0)

                            codeLine = document.get_text(
                                lineBeginIter,
                                document.get_iter_at_line_index(line, 0),
                                True
                            )

                            indention = ""
                            while codeLine[len(indention)] in [" ", "\t", "*"]:
                                indention += codeLine[len(indention)]

                            commentCode = indention + "/* @var " + variableName + " mixed */\n"
                            GLib.idle_add(self.do_textbuffer_insert, document, line-1, 0, commentCode)

            if insertedText == '\n':
                # new line, add indention
                line = textIter.get_line()
                lineBeginIter = document.get_iter_at_line_index(line, 0)

                codeLine = document.get_text(
                    lineBeginIter,
                    document.get_iter_at_line_index(line+1, 0),
                    True
                )

                indention = ""
                while codeLine[len(indention)] in [" ", "\t", "*"]:
                    indention += codeLine[len(indention)]

                GLib.idle_add(self.do_textbuffer_insert, document, line+1, 0, indention)

    def __on_document_changed(self, document, userData=None):
        # make sure the php-file-index gets updated when the text get changed
        if document.get_location() != None:

            filepath = document.get_location().get_path()
            self.invalidate_php_fileindex(filepath)
        return False

    def do_textbuffer_insert(self, document, line, column, text):
        textIter = document.get_iter_at_line_index(line, column)
        document.insert(textIter, text)

    def __on_document_saved(self, document, userData=None):
        start_new_thread(self.__do_on_document_saved, (document, userData))

    def __do_on_document_saved(self, document, userData=None):
        if document.get_location() != None:
            filepath = document.get_location().get_path()
            indexFilepath = self.get_index_filepath()
            indexPathManager = self.get_index_path_manager()
            index = PhpIndex(indexFilepath, indexPathManager=indexPathManager)
            index.reindex_phpfile(filepath)

    ### MENU ITEMS

    def on_index_paths_manager(self, action, data=None):
        if self.get_index_path_manager() != None:
            window = self.getGladeBuilder().get_object("windowIndexPathsManager")
            window.show_all()
        else:
            window = AddiksPhpIndexApp.get().get_window_by_view(self).window
            dialog = Gtk.MessageDialog(window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, "Not a git project!")
            dialog.format_secondary_text("The index-include/-exclude path'scan only be configured for files in a git workspace.")
            dialog.run()

    def on_build_index(self, action, data=None):
        document = self.view.get_buffer()
        if document != None and document.get_location() != None:
            indexPath = self.get_index_filepath()
            gitPath   = self.get_git_directory()
            pathManager = self.get_index_path_manager()
            build_gtk(indexPath, gitPath, pathManager)

    def on_update_index(self, action, data=None):
        document = self.view.get_buffer()
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
        document = self.view.get_buffer()
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
                    if len(block)>3:
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

            self.view.scroll_to_mark(beforeMark, 0.0, True, 0.0, 0.0)

    def on_open_call_view(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()

        line, column = self.get_current_cursor_position()
        if line != None and column != None:
            builder = self.getGladeBuilder()
            window = builder.get_object('windowCallers')
            window.connect('delete-event', lambda w, e: w.hide() or True)
            window.show_all()

            use_statements = self.get_php_fileindex().get_use_statements()
            declaredPositionExpected = self.get_php_fileindex().get_declared_position_by_position(line, column)
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

            listStore = builder.get_object('liststoreCallers')

            filteredUses = {}
            for filePath, line, column, className, functionName in uses:
                phpFileIndex = self.get_php_fileindex(filePath)
                declaredPosition = phpFileIndex.get_declared_position_by_position(line, column+1)
                if declaredPosition[0] == None or declaredPosition == declaredPositionExpected:
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

    def __filteredUsesKey(self, use):
        return use[3] + str(use[1]) + use[4]

    def open_by_position(self, filePath, line, column):
        GLib.idle_add(self.do_open_by_position, filePath, line, column)

    def do_open_by_position(self, filePath, line, column):
        if filePath != None:
            document = self.view.get_buffer()
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

    def on_index_calls(self, current, count):
        print(current + "/" + count)

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
            document = self.view.get_buffer()
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
            self.__phpfiles[filePath] = PhpFileAnalyzer(code, self, self.get_index_storage())
        return self.__phpfiles[filePath]

    def invalidate_php_fileindex(self, filePath=None):
        if filePath == None:
            document = self.view.get_buffer()
            if document != None and document.get_location() != None:
                filePath = document.get_location().get_path()
                filePath = os.path.abspath(filePath)
        if filePath in self.__phpfiles:
            del self.__phpfiles[filePath]

    def get_current_cursor_position(self):
        line = None
        column = None
        document = self.view.get_buffer()
        if document != None and document.get_location() != None:

            insertMark = document.get_insert()
            insertIter = document.get_iter_at_mark(insertMark)
            line   = insertIter.get_line()+1
            column = insertIter.get_line_index()+1
        return (line, column, )

    def get_git_directory(self):
        document = self.view.get_buffer()
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
        window = AddiksPhpIndexApp.get().get_window_by_view(self).window
        dialog = Gtk.MessageDialog(window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, "Build index first!")
        dialog.format_secondary_text("To perform this action, you first need to build the index for this working directory.")
        dialog.run()
        return False

    def get_completion_provider(self):
        if self.__completion_provider == None:
            self.__completion_provider = AutocompleteProvider()
            self.__completion_provider.set_plugin(self)
        return self.__completion_provider
