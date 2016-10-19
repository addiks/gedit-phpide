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

from gi.repository import GLib, Gtk, GObject, Gedit, Gio, Notify, PeasGtk
from AddiksPhpGladeHandler import AddiksPhpGladeHandler
import os

ACTIONS = [
    ['PhpAction',               "PHP",                  "",              None],
    ['BuildIndexAction',        "Build index",          "",              "on_build_index"],
    ['UpdateIndexAction',       "Update index",         "",              "on_update_index"],
    ['ToggleOutlineAction',     "Toogle outline",       "F2",            "on_toggle_outline"],
    ['OpenDeclarationAction',   "Open declaration",     "F3",            "on_open_declaration_view"],
    ['OpenTypeViewAction',      "Open type view",       "<Alt>F3",       "on_open_type_view"],
    ['OpenCallViewAction',      "Open call view",       "<Ctrl>F3",      "on_open_call_view"],
    ['ExportGraphMLAction',     "Export to GraphML",    "<Ctrl><Shift>F3", "on_export_to_graphml"],
    ['SearchIndexAction',       "Search the index",     "<Alt>L",        "on_search_index"],
    ['OpenDepencyViewAction',   "Open depency view",    "",              "on_open_depency_view"],
    ['ManageIndexPathsAction',  "Manage index paths",   "",              "on_index_paths_manager"],
]

class AddiksPhpIndexApp(GObject.Object, Gedit.AppActivatable, PeasGtk.Configurable):
    app = GObject.property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)
        Notify.init("gedit_addiks_phpide")

        if not os.path.exists(os.path.dirname(__file__)+"/gschemas.compiled"):
            pass

        schema_source = Gio.SettingsSchemaSource.new_from_directory(
            os.path.dirname(__file__),
            Gio.SettingsSchemaSource.get_default(),
            False,
        )
        schema = schema_source.lookup('de.addiks.gedit.phpide', False)
        self._settings = Gio.Settings.new_full(schema, None, None)

    def do_activate(self):
        AddiksPhpIndexApp.__instance = self

        if "extend_menu" in dir(self): # build menu for gedit 3.12 (one menu per application)
            submenu = Gio.Menu()
            item = Gio.MenuItem.new_submenu(_("PHP"), submenu)

            mainMenu = self.app.get_menubar()
            mainMenu.append_item(item)

            for actionName, title, shortcut, callbackName in ACTIONS:
                if callbackName != None:
                    item = Gio.MenuItem.new(title, "win.%s" % actionName)
                    if len(shortcut) > 0:
                        item.set_attribute_value("accel", GLib.Variant.new_string(shortcut))
                        self.app.set_accels_for_action("win.%s" % actionName, [shortcut])
                    submenu.append_item(item)

    def get_settings(self):
        return self._settings

    ### SINGLETON

    __instance = None

    @staticmethod
    def get():
        if AddiksPhpIndexApp.__instance == None:
            AddiksPhpIndexApp.__instance = AddiksPhpIndexApp()
        return AddiksPhpIndexApp.__instance

    ### CONFIGURATION

    def do_create_configure_widget(self):
        filename = os.path.dirname(__file__)+"/phpide.glade"
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
