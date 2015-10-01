
from phpfile import PhpFile
from phplexer import token_name
from phplexer import token_num
from gi.repository import Gtk, GtkSource, GObject, Gedit, PeasGtk, Gio
from helpers import *

T_STRING      = token_num("T_STRING")
T_VARIABLE    = token_num("T_VARIABLE")
T_DOC_COMMENT = token_num("T_DOC_COMMENT");

class Proposal(GObject.Object, GtkSource.CompletionProposal):
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


class Provider(GObject.Object, GtkSource.CompletionProvider):
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
            if proposal.get_word() not in fileIndex.get_use_statements():
                fullClassName = proposal.get_additional_info()
                while fullClassName[1] == '\\':
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
        widget.set_size_request(300, 32)
        self._info_label = Gtk.Label()
        self._info_label.set_text(proposal.get_word())
        widget.add(self._info_label)
        widget.show_all()
        return widget # or some Gtk.Widget with extra info

    def do_update_info(self, proposal, info):
        # proposal (GtkSource.CompletionProposal)
        # info (GtkSource.CompletionInfo)
        if proposal.get_additional_info() != None:
            self._info_label.set_text(proposal.get_additional_info())

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
        tokens    = fileIndex.get_tokens()
        proposals = []

        textIter = context.get_iter()
        line   = textIter.get_line()+1
        column = textIter.get_line_index()+1
        tokenIndex = fileIndex.get_token_index_by_position(line, column)
        word = ""
        if tokens[tokenIndex][0] == T_STRING or tokens[tokenIndex-1][1] in ['::', '->']:
            word = tokens[tokenIndex][1]
            tokenIndex -= 1
        if tokens[tokenIndex][0] == T_VARIABLE:
            word = tokens[tokenIndex][1]
        token = tokens[tokenIndex]
        self.colm = token[3]-1
        self.mark_position(textIter)

        rawProposals = []
        classes = []
        functions = []
        members = []
        consts = []

        if tokens[tokenIndex][1] == '::': # members, methods and class-constants
            returnType = fileIndex.get_type_by_token_index(tokenIndex-1)
            self.type = returnType
            className = returnType
            while True:
                namespace, className = get_namespace_by_classname(className)
                functions += storage.get_static_class_methods(namespace, className)
                members   += storage.get_static_class_members(namespace, className)
                consts    += storage.get_class_constants(namespace, className)
                className = storage.get_class_parent(namespace, className)
                if className == None:
                    break
            rawProposals = members + consts
        
        elif tokens[tokenIndex][1] == '->': # members, methods and class-constants
            returnType = fileIndex.get_type_by_token_index(tokenIndex-1)
            self.type = returnType
            className = returnType
            while True:
                namespace, className = get_namespace_by_classname(className)
                functions += storage.get_class_methods(namespace, className)
                members   += storage.get_class_members(namespace, className)
                className = storage.get_class_parent(namespace, className)
                if className == None:
                    break
            rawProposals = members
        
        elif token[0] == T_VARIABLE: # local or global variables
            rawProposals += ["$_GET", "$_POST", "$_COOKIE", "$_SESSION", "$_SERVER"]
            rawProposals += fileIndex.get_variables_in_scope(tokenIndex)
            # TODO: add local vars
            
        else: # classes, constants and functions
            classes   = storage.get_all_classnames(True)
            consts    = storage.get_all_constants()
            functions = storage.get_all_functions()
            rawProposals = consts

        for name in functions:
            if name.startswith(word) or word=="":
                proposals.append(Proposal(name, name[len(word):], "function"))
        for name in classes:
            fullClassName = name
            if "\\" in name:
                name = name[name.rfind("\\")+1:]
            if name.startswith(word) or word=="":
                proposals.append(Proposal(fullClassName, name[len(word):], "class", fullClassName))
        for name in sorted(set(rawProposals)):
            if name.startswith(word) or word=="":
                proposals.append(Proposal(name, name[len(word):]))
        context.add_proposals(self, proposals, True)

