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

from gi.repository import GObject, Gedit
from AddiksPhpIndex import AddiksPhpIndex
from AutocompleteProvider import AutocompleteProvider

class AddiksPhpIndexView(GObject.Object, Gedit.ViewActivatable):
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)
        self.__completion_provider = None

    def do_activate(self):
        window = AddiksPhpIndex.get().get_window_by_view(self.view)
        completion = self.view.get_completion()
        provider = self.get_completion_provider()
        if provider not in completion.get_providers():
            completion.add_provider(provider)

        document = self.view.get_buffer()
        document.connect("changed", self.__on_document_changed)

    def do_deactivate(self):
        pass

    def do_update_state(self):
        pass

    def __on_document_changed(self, document):

        # make sure the php-file-index gets updated when the text get changed
        window = AddiksPhpIndex.get().get_window_by_view(self.view)
        if window != None and document.get_location() != None:
            filepath = document.get_location().get_path()
            window.invalidate_php_fileindex(filepath)
        return False

    ### HELPERS

    def get_completion_provider(self):
        if self.__completion_provider == None:
            window = AddiksPhpIndex.get().get_window_by_view(self.view)
            self.__completion_provider = AutocompleteProvider()
            self.__completion_provider.set_plugin(window)
        return self.__completion_provider

