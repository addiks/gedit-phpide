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

from gi.repository import Gtk, GtkSource, GObject

class AutocompleteProposal(GObject.Object, GtkSource.CompletionProposal):
    __gtype_name__ = "GeditAddiksPHPIDEProposal"

    def __init__(self, word, completion, completionType="none", additionalInfo=None):
        GObject.Object.__init__(self)
        self.__word = word
        self.__completion = completion
        self.__type = completionType
        self.__additional_info = additionalInfo

    def get_word(self):
        return self.__word

    def get_completion(self):
        return self.__completion

    def get_additional_info(self):
        return self.__additional_info

    def get_type(self):
        return self.__type

    def do_get_markup(self):
        return self.__word

    def do_get_info(self):
        return "self.__word"

