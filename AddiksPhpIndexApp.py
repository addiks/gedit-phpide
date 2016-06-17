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

class AddiksPhpIndexApp:

    def __init__(self):
        pass

    ### SINGLETON

    __instance = None

    @staticmethod
    def get():
        if AddiksPhpIndexApp.__instance == None:
            AddiksPhpIndexApp.__instance = AddiksPhpIndexApp()
        return AddiksPhpIndexApp.__instance

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
