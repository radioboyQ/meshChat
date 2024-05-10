import sys

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static


class MeshChatApp(App):
    """A Textual app to chat over Meshtastic radios."""

    CSS_PATH = "TextualUITesting.tcss"

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with Horizontal():
            yield Static("One", classes="box")
            yield Static("Two", classes="box")
            yield Static("Three", classes="box")


if __name__ == "__main__":
    app = MeshChatApp()
    app.run()