from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Footer, Header, Static, Markdown, Log

EXAMPLE_CHAT = """\
User1: Hello World!  
User1: Here is some text  
User2: I'm responding to you!  
"""

Example_Log_Text = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""

# class InputTextBox(Static): # a widget to display an input text box

class meshChatDisplayApp(App):
    """A Textual app to manage stopwatches."""
    CSS_PATH = "python_display_textual.tcss"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="app-grid"):
            with ScrollableContainer(id="chatlog"):
                yield Static(f"{Example_Log_Text}"*3)
            with Container(id="nodebox"):
                yield Static("User"*10)
            with Container(id="channelbox"):
                yield Static("Channel"*5)
        yield Static("TextEntryBox", id="textentrybox")



if __name__ == "__main__":
    app = meshChatDisplayApp()
    app.run()  # this runs the app, puts terminal into application mode
