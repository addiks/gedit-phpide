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

from gi.repository import Gtk, GObject, Gedit
from AddiksPhpIndexApp import AddiksPhpIndexApp

import os

class AddiksPhpIndexWindow(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        AddiksPhpIndexApp.get().register_window(self)

        plugin_path = os.path.dirname(__file__)
        self._ui_manager = self.window.get_ui_manager()
        actions = [
            ['PhpAction',               "PHP",                  "",        None],
            ['BuildIndexAction',        "Build index",          "",         self.on_build_index],
            ['UpdateIndexAction',       "Update index",         "",         self.on_update_index],
            ['ToggleOutlineAction',     "Toogle outline",       "<Ctrl>F1", self.on_toggle_outline],
            ['OpenTypeViewAction',      "Open type view",       "<Ctrl>F2", self.on_open_type_view],
            ['OpenDeclarationAction',   "Open declaration",     "<Ctrl>F3", self.on_open_declaration_view],
            ['OpenCallViewAction',      "Open call view",       "<Ctrl>F4", self.on_open_call_view],
            ['SearchIndexAction',       "Search the index",     "<Ctrl>L",  self.on_search_index],
            ['OpenDepencyViewAction',   "Open depency view",    "",         self.on_open_depency_view],
            ['ManageIndexPathsAction',  "Manage index paths",   "",         self.on_index_paths_manager],
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
        AddiksPhpIndexApp.get().unregister_window(self)

    def do_update_state(self):
        document = self.window.get_active_document()

        if document != None and document.get_location() != None:
            path = document.get_location().get_path()
            if path[-4:] != '.php' and path[-6:] != '.phtml':
                self._ui_manager.remove_ui(self._ui_merge_id)

    ### MENU EVENTS

    def on_index_paths_manager(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_index_paths_manager(action, data)

    def on_build_index(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_build_index(action, data)

    def on_update_index(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_update_index(action, data)

    def on_open_declaration_view(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_open_declaration_view(action, data)

    def on_search_index(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_search_index(action, data)

    def on_open_type_view(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_open_type_view(action, data)

    def on_toggle_outline(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_toggle_outline(action, data)

    def on_open_call_view(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_open_call_view(action, data)

    def on_open_depency_view(self, action, data=None):
        if not self.is_index_built():
            return self.on_index_not_build()
        print("Open depency-view")

    ### HELPERS

    def get_active_view(self):
        geditView = self.window.get_active_view()
        pluginView = AddiksPhpIndexApp.get().get_plugin_view_by_gedit_view(geditView)
        return pluginView

