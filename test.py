
from gi.repository import Gtk, GtkSource, GObject, PeasGtk, Gio

class TextCompletionProvider(GtkSource.CompletionProvider, GObject.Object):
  
    def __init__(self):
        pass

    def activate_proposal(proposal, textIter):
        print("ACTIVATE_PROPOSAL")
        # proposal (GtkSource.CompletionProposal)
        # textIter (Gtk.TextIter)

        return False

    def get_activation():
        print("GET_ACTIVATION")
        GtkSource.CompletionActivation.NONE
        # INTERACTIVE    => on every insert into text-buffer
        # USER_REQUESTED => only on ctrl+space

    def get_icon():
        print("GET_ICON")
        return None # or GdkPixbuf.Pixbuf

    def get_info_widget(proposal):
        print("GET_INFO_WIDGET")
        return None # or some Gtk.Widget with extra info

    def get_interactive_delay():
        print("GET_INTERACTIVE_DELAY")
        return -1

    def get_name():
        print("GET_NAME")
        return "Addiks PHP-IDE"

    def get_priority():
        print("GET_PRIORITY")
        return 0 # sort order

    def get_start_iter(context, proposal, textIter):
        print("GET_START_ITER")
        # context  (GtkSource.CompletionContext)
        # proposal (GtkSource.CompletionProposal)
        # textIter (Gtk.TextIter)
        return False

    def match(context):
        print("MATCH")
        # context  (GtkSource.CompletionContext)
        return False

    def populate(context):
        print("POPULATE")
        # context  (GtkSource.CompletionContext)
        storage = self.__addiks_plugin.get_index_storage()
        proposals = []
        for className in storage.get_all_classnames():
            proposals.append(GtkSource.CompletionProposal(className))
        context.add_proposals(self, proposals, True)
        pass

    def update_info(proposal, info):
        print("UPDATE_INFO")
        # proposal (GtkSource.CompletionProposal)
        # info (GtkSource.CompletionInfo)
        pass

textBuffer = Gtk.TextBuffer()
textView = GtkSource.View()
completion = GtkSource.Completion()

