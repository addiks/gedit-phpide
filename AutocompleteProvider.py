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

from PHP.PhpFile import PhpFile
from PHP.get_namespace_by_classname import get_namespace_by_classname
from AutocompleteProposal import AutocompleteProposal
from PHP.phplexer import token_name, token_num
from gi.repository import Gtk, GtkSource, GObject
import re

T_STRING      = token_num("T_STRING")
T_VARIABLE    = token_num("T_VARIABLE")
T_DOC_COMMENT = token_num("T_DOC_COMMENT");
T_COMMENT     = token_num("T_COMMENT");

class AutocompleteProvider(GObject.Object, GtkSource.CompletionProvider):
   # __gtype_name__ = "GeditAddiksPHPIDEProvider"

    def __init__(self):
        GObject.Object.__init__(self)
        self.mark = None
        self.colm = None
        self.type = None
        self._info_label = Gtk.Label()

    def set_plugin(self, plugin):
        self.__addiks_plugin = plugin

    def mark_position(self, iter):
        self.iter = iter
        if not self.mark:
            self.mark = iter.get_buffer().create_mark(None, iter, True)
        else:
            self.mark.get_buffer().move_mark(self.mark, iter)

    def do_activate_proposal(self, proposal, textIter):
        # proposal (GtkSource.CompletionProposal)
        # textIter (Gtk.TextIter)
        completion = proposal.get_completion()
        fileIndex = self.__addiks_plugin.get_php_fileindex()
        tokens = fileIndex.get_tokens()

        if proposal.get_type() == 'function':
            completion += "()"

        textIter.get_buffer().insert(textIter, completion)

        if proposal.get_type() == 'class':
            fullClassName = proposal.get_additional_info()
            if fullClassName[0] != '\\':
                fullClassName = '\\' + fullClassName
            if fullClassName not in fileIndex.get_use_statements().values():
                while fullClassName[0] == '\\':
                    fullClassName = fullClassName[1:]
                useStmsIter = textIter.copy()
                tokenIndex = fileIndex.get_use_statement_index()

                appendix = ""
                if tokenIndex != None:
                    useStmsIter.set_line(tokens[tokenIndex][2])
                    useStmsIter.set_line_index(tokens[tokenIndex][3]-1)
                elif tokens[1][0] == T_DOC_COMMENT:
                    useStmsIter.set_line(tokens[2][2]-1)
                    useStmsIter.set_line_index(tokens[2][3]-1)
                    appendix = "\n"
                else:
                    useStmsIter.set_line(1)
                    useStmsIter.set_line_index(0)
                textIter.get_buffer().insert(useStmsIter, "use "+fullClassName+";\n"+appendix)

        return True

    def do_get_activation(self):
        return GtkSource.CompletionActivation.USER_REQUESTED
        # NONE           => this one is self-explanatory
        # INTERACTIVE    => on every insert into text-buffer
        # USER_REQUESTED => only on ctrl+space

    def do_get_icon(self):
        return None # or GdkPixbuf.Pixbuf

    def do_get_info_widget(self, proposal):
        widget = Gtk.ScrolledWindow()
        widget.set_size_request(500, 300)
        self._info_label = Gtk.Label()
        self._info_label.set_text(proposal.get_word())
        self.do_update_info(proposal)
        widget.add(self._info_label)
        widget.show_all()
        return widget # or some Gtk.Widget with extra info

    def do_update_info(self, proposal, info = None):
        # proposal (GtkSource.CompletionProposal)
        # info (GtkSource.CompletionInfo)
        storage   = self.__addiks_plugin.get_index_storage()

        labelText = None
        if proposal.get_type() == 'function':
            labelText = storage.get_constant_doccomment(proposal.get_word())

        elif proposal.get_type() == 'class':
            if proposal.get_additional_info() != None:
                fullClassName = proposal.get_additional_info()
                namespace, className = get_namespace_by_classname(fullClassName)
                labelText = storage.get_class_doccomment(namespace, className)

        elif proposal.get_type() == 'member':
            labelText = storage.get_constant_doccomment(proposal.get_word())

        elif proposal.get_type() == 'const':
            labelText = storage.get_constant_doccomment(proposal.get_word())

        else:
            print("unknown: " + proposal.get_type())

        if labelText != None:
            self._info_label.set_text(labelText)

    def do_get_name(self):
        if self.type == None:
            return "[No type detected]"
        else:
            return self.type

    def do_get_start_iter(self, context, proposal, textIter):
        if not self.mark:
            return False
        textBuffer = self.mark.get_buffer()
        textIter.assign(textBuffer.get_iter_at_mark(self.mark))
        return True

    def do_match(self, context):
        return True

    def do_populate(self, context):
        if self.__addiks_plugin == None:
            return

        storage   = self.__addiks_plugin.get_index_storage()
        fileIndex = self.__addiks_plugin.get_php_fileindex()
        proposals = []

        textIter = context.get_iter()
        line   = textIter.get_line()+1
        column = textIter.get_line_index()+1

        tokens    = fileIndex.get_tokens()
        tokenIndex = fileIndex.get_token_index_by_position(line, column)

        word = ""
        if tokens[tokenIndex][0] == T_COMMENT:
            lineInComment = line - tokens[tokenIndex][2]
            columnInComment = column - tokens[tokenIndex][3] - 1
            commentLines = tokens[tokenIndex][1].split("\n")
            commentLine = commentLines[lineInComment]
            while re.match("[a-zA-Z0-9_]", commentLine[columnInComment]):
                word = commentLine[columnInComment] + word
                columnInComment -= 1
        if tokens[tokenIndex][0] == T_STRING or tokens[tokenIndex-1][1] in ['::', '->']:
            word = tokens[tokenIndex][1]
            tokenIndex -= 1
        if tokens[tokenIndex][0] == T_VARIABLE:
            word = tokens[tokenIndex][1]
        token = tokens[tokenIndex]
        self.colm = token[3]-1
        self.mark_position(textIter)

        members = []
        functions = []
        consts = []
        variables = []

        if tokens[tokenIndex][1] == '::': # static members, static methods and class-constants
            returnType = fileIndex.get_type_by_token_index(tokenIndex-1)
            self.type = returnType
            className = returnType
            members = []
            while True:
                namespace, className = get_namespace_by_classname(className)
                functions += storage.get_static_class_methods(namespace, className)
                members   += storage.get_static_class_members(namespace, className)
                consts    += storage.get_class_constants(namespace, className)
                className = storage.get_class_parent(namespace, className)
                if className == None:
                    break

        elif tokens[tokenIndex][1] == '->': # members and methods
            returnType = fileIndex.get_type_by_token_index(tokenIndex-1)
            self.type = returnType
            className = returnType
            members = []
            while True:
                namespace, className = get_namespace_by_classname(className)
                functions += storage.get_class_methods(namespace, className)
                members   += storage.get_class_members(namespace, className)
                className = storage.get_class_parent(namespace, className)
                if className == None:
                    break

        elif token[0] == T_VARIABLE: # local or global variables
            variables += ["$_REQUEST", "$_GET", "$_POST", "$_COOKIE", "$_SESSION", "$_SERVER"]
            variables += fileIndex.get_variables_in_scope(tokenIndex)

        else: # classes, constants and functions
            classes   = storage.get_all_classnames(True)
            consts    = storage.get_all_constants()
            functions = storage.get_all_functions()
            for name in classes:
                fullClassName = name
                if "\\" in name:
                    name = name[name.rfind("\\")+1:]
                if name.startswith(word) or word=="":
                    proposals.append(AutocompleteProposal(fullClassName, name[len(word):], "class", fullClassName))

        for name in functions:
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "function"))

        for name in set(members):
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "member"))

        for name in set(consts):
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "const"))

        for name in variables:
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "variable"))

        if len(proposals) < 10000:
            proposals.sort(key=self._sortKeyForProposal)

            context.add_proposals(self, proposals, True)

    def _sortKeyForProposal(self, proposal):
        key = None

        if proposal.get_type() == "class":
            namespace, className = get_namespace_by_classname(proposal.get_word())
            key = self.__sortKey(className) + self.__sortKey(namespace)
        else:
            key = self.__sortKey(proposal.get_word())

        return key

    def __sortKey(self, name):
        length = len(name)
        length = str(length).zfill(4)
        return length + name

