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

from gi.repository import Gtk, GObject, Gedit, Gio
from AddiksPhpIndexApp import AddiksPhpIndexApp, ACTIONS

import os

class AddiksPhpIndexWindow(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._ui_manager = None
        self._is_ui_added = False

    def do_activate(self):
        AddiksPhpIndexApp.get().register_window(self)

        self._actions = Gtk.ActionGroup("AddiksPhpMenuActions")
        for actionName, title, shortcut, callbackName in ACTIONS:
            action = Gio.SimpleAction(name=actionName)
            callback = None
            if callbackName != None:
                callback = getattr(self, callbackName)
                action.connect('activate', callback)
            self.window.add_action(action)
            self.window.lookup_action(actionName).set_enabled(True)

            self._actions.add_actions([(actionName, Gtk.STOCK_INFO, title, shortcut, "", callback),])

        if "get_ui_manager" in dir(self.window):# build menu for gedit 3.10 (global menu per window)
            self._ui_manager = self.window.get_ui_manager()
            self._ui_manager.insert_action_group(self._actions)

        self.do_update_state()

    def do_deactivate(self):
        AddiksPhpIndexApp.get().unregister_window(self)

    def do_update_state(self):
        document = self.window.get_active_document()

        if self._ui_manager != None and document != None and document.get_location() != None:
            path = document.get_location().get_path()
            if path[-4:] != '.php' and path[-6:] != '.phtml' and self._is_ui_added:
                self._ui_manager.remove_ui(self._ui_merge_id)
                self._is_ui_added = False

            elif (path[-4:] == '.php' or path[-6:] == '.phtml') and not self._is_ui_added:
                self._is_ui_added = True
                plugin_path = os.path.dirname(__file__)
                with open(plugin_path + "/menubar.xml", "r", encoding = "ISO-8859-1") as f:
                    menubarXml = f.read()
                self._ui_merge_id = self._ui_manager.add_ui_from_string(menubarXml)
                self._ui_manager.ensure_update()

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

    def on_export_to_graphml(self, action, data=None):
        pluginView = self.get_active_view()
        pluginView.on_export_to_graphml(action, data)

    ### HELPERS

    def get_active_view(self):
        geditView = self.window.get_active_view()
        pluginView = AddiksPhpIndexApp.get().get_plugin_view_by_gedit_view(geditView)
        return pluginView
