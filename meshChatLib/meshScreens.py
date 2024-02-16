import datetime

from textual.app import App, ComposeResult, RenderResult
from textual.containers import ScrollableContainer, Container, VerticalScroll, Vertical, Grid, Center, Middle
from textual import events
from textual.css.query import NoMatches
from textual.screen import Screen, ModalScreen
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import (Header, Footer, Log, Placeholder, Static, Label, Button, LoadingIndicator, TextArea,
                             Markdown, RichLog, Input, ListView, ListItem, OptionList, ProgressBar)
class MainChatScreen(Screen):

    BINDINGS = [("ctrl+d", "toggle_dark", "Dark Mode"),
                ("ctrl+q", "request_quit", "Quit")]

    def __init__(
            self,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,):
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        yield Vertical(
                OptionList(classes="nodes", id="nodes"),
                        Placeholder(label="Channels", classes="box", id="channels"), id="left_col")
        yield Vertical(
                VerticalScroll(
                    RichLog(highlight=True, markup=True)),
                    # Placeholder(label="Main Chat", classes="box", id="main_chat")),
                Input(placeholder="Send messages", classes="box", id="main_chat_text_input", type="text"), id="center_col")
        yield Vertical(
            Placeholder(label="Radio Information", classes="box", id="radio_info"),
            Button("Add Nodes", classes="box", id="add_node"), id="right_col"
        )
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self) -> None:
        try:
            input_box = self.query_one(Input)
            input_box.focus()
        except:
            pass

class QuitScreen(ModalScreen[bool]):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.dismiss(True)
        else:
            self.dismiss(False)


class PollingForRadioScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Grid(
            LoadingIndicator(name="Waiting on a radio", id="loadingbar"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.dismiss(True)
        else:
            self.dismiss(False)