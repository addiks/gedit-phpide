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
gi.require_version('Notify', '0.7')

from gi.repository import GLib, Gtk, GtkSource, GObject, Gedit, Gio, Notify, PeasGtk
import os

from .AddiksPhpGladeHandler import AddiksPhpGladeHandler

from .PHP.functions import get_namespace_by_classname

ACTIONS = [
    ['PhpAction',               "PHP",                  "",                None],
    ['BuildIndexAction',        "Build index",          "",                "on_build_index"],
    ['UpdateIndexAction',       "Update index",         "",                "on_update_index"],
    ['ToggleOutlineAction',     "Toogle outline",       "F2",              "on_toggle_outline"],
    ['ShowInfoWindowAction',    "Show info window",     "<Ctrl>F2",        "on_show_info_window"],
    ['OpenDeclarationAction',   "Open declaration",     "F3",              "on_open_declaration_view"],
    ['OpenTypeViewAction',      "Open type view",       "<Alt>F3",         "on_open_type_view"],
    ['OpenCallViewAction',      "Open call view",       "<Ctrl>F3",        "on_open_call_view"],
    ['ExportGraphMLAction',     "Export to GraphML",    "<Ctrl><Shift>F3", "on_export_to_graphml"],
    ['SearchIndexAction',       "Search the index",     "<Alt>L",          "on_search_index"],
    ['OpenDepencyViewAction',   "Open depency view",    "",                "on_open_depency_view"],
    ['ManageIndexPathsAction',  "Manage index paths",   "",                "on_index_paths_manager"],
]

class AddiksPHPIDEApp(GObject.Object, Gedit.AppActivatable, PeasGtk.Configurable):
    app = GObject.property(type=Gedit.App)
    _info_window = None
    _info_buffer = None
    _settings = None

    def __init__(self):
        GObject.Object.__init__(self)
        Notify.init("gedit_addiks_phpide")

        if not os.path.exists(os.path.dirname(__file__)+"/assets/gschemas.compiled"):
            pass

        schema_source = Gio.SettingsSchemaSource.new_from_directory(
            os.path.dirname(__file__)+"/assets",
            Gio.SettingsSchemaSource.get_default(),
            False,
        )
        schema = schema_source.lookup('de.addiks.gedit.phpide', False)
        self._settings = Gio.Settings.new_full(schema, None, None)

    def do_activate(self):
        AddiksPHPIDEApp.__instance = self

        # Gedit.App
        app = self.app

        if "extend_menu" in dir(self): # build menu for gedit 3.12+ (one menu per application)
            submenu = Gio.Menu()
            phpMenuItem = Gio.MenuItem.new_submenu(_("PHP"), submenu)

            for actionName, title, shortcut, callbackName in ACTIONS:
                if callbackName != None:
                    item = Gio.MenuItem.new(title, "win.%s" % actionName)
                    if len(shortcut) > 0:
                        item.set_attribute_value("accel", GLib.Variant.new_string(shortcut))
                        self.app.set_accels_for_action("win.%s" % actionName, [shortcut])
                    submenu.append_item(item)

            mainMenu = self.app.get_menubar()
            if mainMenu is not None:
                mainMenu.append_item(phpMenuItem)

            else:
                toolsMenu = self.extend_menu("tools-section")
                if toolsMenu is not None:
                    toolsMenu.prepend_menu_item(phpMenuItem)

            # This works for gedit 3.22; it add's PHP menu to app-menu in the top-bar
            # (Not really how i want it to work, but it's the only way that i got the menu working in 3.22)
            if "get_app_menu" in dir(app):
                appMenu = app.get_app_menu()
                if appMenu is not None:
                    appMenu.append_item(phpMenuItem)

    def get_settings(self):
        return self._settings

    ### SINGLETON

    __instance = None

    @staticmethod
    def get():
        if AddiksPHPIDEApp.__instance == None:
            AddiksPHPIDEApp.__instance = AddiksPHPIDEApp()
        return AddiksPHPIDEApp.__instance

    ### CONFIGURATION

    def do_create_configure_widget(self):
        filename = os.path.dirname(__file__)+"/assets/phpide.glade"
        self._glade_builder = Gtk.Builder()
        self._glade_builder.add_objects_from_file(filename, ["gridConfig"])
        self._glade_handler = AddiksPhpGladeHandler(self, self._glade_builder)
        self._glade_builder.connect_signals(self._glade_handler)
        for key, objectName, attributeName in [
            ["graphml-execute-pattern", "entryConfigGraphMLExecutePattern", "text"]
        ]:
            widget = self._glade_builder.get_object(objectName)
            self._settings.bind(key, widget, attributeName, Gio.SettingsBindFlags.DEFAULT)
        return self._glade_builder.get_object("gridConfig")

    ### WINDOW / VIEW MANAGEMENT

    windows = []

    def register_window(self, window):
        if window not in self.windows:
            self.windows.append(window)

    def unregister_window(self, window):
        if window in self.windows:
            self.windows.remove(window)

    def get_window_by_view(self, view):
        if view in dir(view):
            view = view.view
        for window in self.windows:
            if view in window.window.get_views():
                return window

    ### VIEWS

    views = []

    def get_plugin_view_by_gedit_view(self, geditView):
        for pluginView in self.views:
            if pluginView.view == geditView:
                return pluginView

    def register_view(self, view):
        if view not in self.views:
            self.views.append(view)

    def unregister_view(self, view):
        if view in self.views:
            self.views.remove(view)

    ### INFO WINDOW

    def show_info_window(self, phpIndexView):
        if self._info_window == None:
            self.__build_info_window()
        self._info_window.show_all()
        self.update_info_window(phpIndexView)

    def update_info_window(self, phpIndexView, declaration=None):
        if self._info_window != None:
            fileAnalyzer = phpIndexView.get_php_fileindex()
            infoWindow = self._info_window
            sourceBuffer = self._info_buffer


            if declaration != None:
                decType, decName, containingClass = declaration

            else:
                line, column = phpIndexView.get_current_cursor_position()
                decType, decName, containingClass = fileAnalyzer.get_declaration_by_position(line, column)

                if decType == "class" and containingClass == None:
                    decName = fileAnalyzer.map_classname_by_use_statements(decName)

            storage = phpIndexView.get_index_storage()

            infoText = ""
            if decType != None:
                infoText = self.build_info_text(storage, decType, decName, containingClass)

                infoWindow.set_title("Gedit - Definition of: %s" % decName)

            else:
                infoWindow.set_title("Gedit - Definition of: {Nothing yet}")

            phpLanguage = phpIndexView.view.get_buffer().get_language()
            sourceBuffer.set_highlight_syntax(True)
            sourceBuffer.set_language(phpLanguage)
            sourceBuffer.set_text(infoText)

    def build_info_text(self, storage, decType, decName, containingClass=None):
        prefix = "<?php\n\n"
        labelText = None
        filePath = None
        infoText = None

        if decType == 'function':
            namespace = containingClass
            labelText = storage.get_function_doccomment(namespace, decName)

        elif decType in ['const', 'constant']:
            labelText = storage.get_constant_doccomment(decName)

        elif decType == 'class':
            if containingClass != None:
                namespace, className = get_namespace_by_classname(containingClass)

            else:
                namespace, className = get_namespace_by_classname(decName)

            filePath, line, column = storage.get_class_position(namespace, className)

            infoText = "<?php\n\nnamespace "+namespace+";\n\n"

            docComment = storage.get_class_doccomment(namespace, className)
            if docComment != None:
                infoText += docComment + "\n"

            if filePath != None and line != None:
                infoText += self.__get_text_until_bracket(filePath, line, column)

            for methodName in storage.get_class_methods(namespace, className):
                methodFilePath, methodLine, methodColumn = storage.get_method_position(namespace, className, methodName)

                methodLabelText = self.__get_text_until_bracket(methodFilePath, methodLine, methodColumn)

                if methodLabelText != None:
                    infoText += "\n" + methodLabelText

        elif decType == 'method':
            if containingClass != None:
                namespace, className = get_namespace_by_classname(containingClass)
                labelText = storage.get_method_doccomment(namespace, className, decName)
                filePath, line, column = storage.get_method_position(namespace, className, decName)
                prefix = "<?php\n\nnamespace "+namespace+";\n\n"

        elif decType == 'member':
            if containingClass != None:
                namespace, className = get_namespace_by_classname(containingClass)
                labelText = storage.get_member_doccomment(namespace, className, decName)

        else:
            print("unknown declaration-type: " + decType)

        if infoText == None:
            if labelText == None:
                labelText = ""

            if filePath != None and line != None:
                if len(labelText) > 0:
                    labelText += "\n"
                labelText += self.__get_text_until_bracket(filePath, line, column)

            if len(labelText) > 0:
                labelText = prefix + labelText
            infoText = labelText

        return infoText

    def __get_text_until_bracket(self, filePath, lineNr, columnNr):
        code = ""
        if filePath != "INTERNAL":
            with open(filePath, "r") as readHandle:
                lines = readHandle.readlines()
                lines = lines[lineNr-1:]
                code = "\n".join(lines)
                pos = len(code)
                for needle in ["{", ";", "\n"]:
                    posNeedle = code.find(needle)
                    if posNeedle > 0 and pos > posNeedle:
                        pos = posNeedle
                code = code[0:pos]
        return code


    def __build_info_window(self):
        infoWindow = Gtk.Window()
        scrolledWindow = Gtk.ScrolledWindow()
        sourceView = GtkSource.View()
        sourceBuffer = GtkSource.Buffer()

        sourceView.editable = False
        scrolledWindow.set_size_request(500, 300)

        sourceView.set_buffer(sourceBuffer)
        scrolledWindow.add(sourceView)
        infoWindow.add(scrolledWindow)

        self._info_buffer = sourceBuffer
        self._info_window = infoWindow
