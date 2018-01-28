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

from gi.repository import GLib, Gtk, GtkSource, GObject
from _thread import start_new_thread
import re

from .AutocompleteProposal import AutocompleteProposal
from .AddiksPHPIDEApp import AddiksPHPIDEApp

from .PHP.functions import get_namespace_by_classname
from .PHP.phplexer import token_name, token_num

T_STRING      = token_num("T_STRING")
T_VARIABLE    = token_num("T_VARIABLE")
T_DOC_COMMENT = token_num("T_DOC_COMMENT")
T_COMMENT     = token_num("T_COMMENT")

class AutocompleteProvider(GObject.Object, GtkSource.CompletionProvider):
   # __gtype_name__ = "GeditAddiksPHPIDEProvider"

    def __init__(self):
        GObject.Object.__init__(self)
        self.mark = None
        self.colm = None
        self.type = None

    def set_plugin(self, pluginView):
        self.__pluginView = pluginView

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
        storage   = self.__pluginView.get_index_storage()
        fileIndex = self.__pluginView.get_php_fileindex()
        tokens = fileIndex.get_tokens()

        if proposal.get_type() in ['function', 'method']:
            line = textIter.get_line() + 1
            column = textIter.get_line_offset() + 1
            tokenIndex = fileIndex.get_token_index_by_position(line, column)
            if len(tokens) == tokenIndex-1 or tokens[tokenIndex+1][1] != "(":
                completion += "("

                arguments = []
                if proposal.get_type() == 'function':
                    namespace = proposal.get_additional_info()
                    arguments = storage.get_function_arguments(namespace, proposal.get_word())

                elif proposal.get_type() == 'method':
                    if proposal.get_additional_info() != None:
                        fullClassName = proposal.get_additional_info()
                        namespace, className = get_namespace_by_classname(fullClassName)
                        arguments = storage.get_method_arguments(namespace, className, proposal.get_word())

                if type(arguments) == list and len(arguments) > 0:
                    argumentsCodes = []
                    for argumentRow in arguments:
                        argumentsCode = None
                        if type(argumentRow) == str:
                            if len(argumentRow) > 0 and argumentRow[0] != "$":
                                argumentRow = "$" + argumentRow
                            argumentsCode = argumentRow
                        elif len(argumentRow) > 3:
                            argumentsCode = ""

                        elif len(argumentRow) == 3:
                            argumentType, argumentsCode, argumentDefaultValue = argumentRow
                        elif len(argumentRow) == 2:
                            argumentDefaultValue = None
                            argumentType, argumentsCode = argumentRow
                        if argumentsCode != None:
                            argumentsCodes.append(argumentsCode)
                    completion += ", ".join(argumentsCodes)

                completion += ")"

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
        sourceView = GtkSource.View()
        sourceView.editable = False
        sourceView.set_property("show-line-numbers", True)

        phpLanguage = self.__pluginView.view.get_buffer().get_language()

        sourceBuffer = sourceView.get_buffer()
        sourceBuffer.set_highlight_syntax(True)
        sourceBuffer.set_language(phpLanguage)

        infoLabel = Gtk.Label()
        infoLabel.set_text(proposal.get_word())

        start_new_thread(self.__fill_info_widget, (sourceBuffer, infoLabel, proposal))

        infoWidget = Gtk.ScrolledWindow()
        infoWidget.set_size_request(500, 300)
        infoWidget.add(sourceView)
        infoWidget.show_all()

        return infoWidget # or some Gtk.Widget with extra info

    def __fill_info_widget(self, sourceBuffer, infoLabel, proposal):
        storage = self.__pluginView.get_index_storage()
        decType = proposal.get_type()
        decName = proposal.get_word()
        containingClass = proposal.get_additional_info()

        labelText = AddiksPHPIDEApp.get().build_info_text(storage, decType, decName, containingClass)

        GLib.idle_add(self.__do_fill_info_widget, sourceBuffer, infoLabel, proposal, labelText)

    def __do_fill_info_widget(self, sourceBuffer, infoLabel, proposal, labelText):
        if len(labelText) > 0:
            infoLabel.set_text(labelText)
            sourceBuffer.set_text(labelText)

        decType = proposal.get_type()
        decName = proposal.get_word()
        containingClass = proposal.get_additional_info()

        AddiksPHPIDEApp.get().update_info_window(self.__pluginView, (decType, decName, containingClass))

    def do_get_name(self):
        if self.type == None:
            return "[No type detected]"
        else:
            return self.type

    def do_get_start_iter(self, context, proposal, textIter=None):
        if not self.mark:
            return False
        if textIter == None:
            textIter = context.get_iter()
            if type(textIter) is not Gtk.TextIter:
                hasIter, textIter = textIter
        textBuffer = self.mark.get_buffer()
        textIter.assign(textBuffer.get_iter_at_mark(self.mark))
        return True

    def do_match(self, context):
        return True

    def do_populate(self, context):
        if self.__pluginView == None:
            return

        storage   = self.__pluginView.get_index_storage()
        fileIndex = self.__pluginView.get_php_fileindex()
        proposals = []

        textIter = context.get_iter()
        if type(textIter) is not Gtk.TextIter:
            hasIter, textIter = textIter
        line   = textIter.get_line()+1
        column = textIter.get_line_index()

        tokens    = fileIndex.get_tokens()
        tokenIndex = fileIndex.get_token_index_by_position(line, column + 1)

        word = ""
        if tokens[tokenIndex][0] in [T_COMMENT, T_DOC_COMMENT]:
            lineInComment = line - tokens[tokenIndex][2]
            columnInComment = column - 1
            if lineInComment == 0:
                columnInComment -= (tokens[tokenIndex][3] - 1)
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
        methods = []
        consts = []
        variables = []

        className = None

        if tokens[tokenIndex][1] == '::': # static members, static methods and class-constants
            returnType = fileIndex.get_type_by_token_index(tokenIndex-1)
            self.type = returnType
            className = returnType
            members = []
            while True:
                namespace, className = get_namespace_by_classname(className)
                methods   += storage.get_static_class_methods(namespace, className)
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
            parentClassName = className

            while True:
                namespace, parentClassName = get_namespace_by_classname(parentClassName)

                traitNamespace = namespace
                for traitClassName in storage.get_class_traits(traitNamespace, parentClassName, True):
                    traitNamespace, traitClassName = get_namespace_by_classname(traitClassName)
                    methods += storage.get_class_methods(traitNamespace, traitClassName)
                    members += storage.get_class_members(traitNamespace, traitClassName)

                methods += storage.get_class_methods(namespace, parentClassName)
                members += storage.get_class_members(namespace, parentClassName)
                parentClassName = storage.get_class_parent(namespace, parentClassName)
                if parentClassName == None:
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

        for name in methods:
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "method", className))

        for name in set(members):
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "member", className))

        for namespace, name in functions:
            if name.startswith(word) or word=="":
                proposals.append(AutocompleteProposal(name, name[len(word):], "function", namespace))

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
