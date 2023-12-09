# Standard library imports
from time import strftime, localtime
from pprint import pprint

# Installed 3rd party modules
import click
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from rich import box, inspect
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from textual.app import App, ComposeResult, RenderResult
from textual.containers import ScrollableContainer, Container, VerticalScroll, Vertical, Grid
from textual import events
from textual.css.query import NoMatches
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Log, Placeholder, Static, Label, Button, LoadingIndicator, TextArea, Markdown, RichLog

# Import custom status symbols
from meshChatLib import (info_blue_splat,
                       info_green_splat,
                       warning_fmt,
                       prompt_yellow_question,
                       error_fmt,
                       success_green,
                       warning_triangle_yellow)
from meshChatLib.setup import Setup, Parser

CODE = '''\
def loop_first_last(values: Iterable[T]) -> Iterable[tuple[bool, bool, T]]:
    """Iterate and generate a tuple with a flag for first and last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    first = True
    for value in iter_values:
        yield first, False, previous_value
        first = False
        previous_value = value
    yield first, True, previous_value\
'''




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

class MainChatScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Vertical(Placeholder(label="DMs", classes="box", id="dms"),
                       Placeholder(label="Channels", classes="box", id="channels"), id="left_col")
        yield Vertical(
                VerticalScroll(
                    RichLog(highlight=True, markup=True)),
                    # Placeholder(label="Main Chat", classes="box", id="main_chat")),
                Placeholder(label="Text Input", classes="box", id="main_chat_text_input"), id="center_col")
        yield Vertical(
            Placeholder(label="Radio Information", classes="box", id="radio_info"), id="right_col"
        )
        yield Header(show_clock=True)
        yield Footer()



class RadioSettingsScreen(Screen):

    def compose(self) -> ComposeResult:
        radio_info_table = Table(title="Radio Configuration Table", box=box.ASCII_DOUBLE_HEAD)
        # Add all of the columns for the table
        radio_info_table.add_column("local_node_id")
        radio_info_table.add_column("firmware_version")
        radio_info_table.add_column("device_state_version")
        radio_info_table.add_column("canShutdown")
        radio_info_table.add_column("hasWifi")
        radio_info_table.add_column("hasBluetooth")
        radio_info_table.add_column("position_flags")
        radio_info_table.add_column("hw_model")
        radio_info_table.add_column("macaddr")
        radio_info_table.add_column("long_name")
        radio_info_table.add_column("short_name")
        radio_info_table.add_column("first_seen")
        radio_info_table.add_column("last_seen")

        # local_node_id = local_node_id,
        # long_name = long_name,
        # short_name = short_name,
        # firmware_version = self.interface.metadata.firmware_version,
        # device_state_version = self.interface.metadata.device_state_version,
        # macaddr = macaddr,
        # canShutdown = self.interface.metadata.canShutdown,
        # hasWifi = self.interface.metadata.hasWifi,
        # hasBluetooth = self.interface.metadata.hasBluetooth,
        # position_flags = self.interface.metadata.position_flags,
        # hw_model = self.interface.metadata.hw_model,
        # first_seen = datetime.datetime.now(),
        # last_seen = datetime.datetime.now()

        yield Header(show_clock=True)
        yield Footer()


class HelpScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Placeholder("Help Screen")
        yield Header(show_clock=True, name="\"Help\"", id="header")
        yield Footer()


class meshChatApp(App):
    """Starting meshChat client"""
    TITLE = "meshChat"
    SUB_TITLE = "The finest off grid chat application"
    CSS_PATH = "meshChatLib/meshLibTest.tcss"
    # A binding for q and for Q to quit the app
    BINDINGS = [("ctrl+d", "toggle_dark", "Dark Mode"),
                ("ctrl+q", "request_quit", "Quit"),
                ("ctrl+t", "switch_mode('meshchat')", "meshChat"),
                ("ctrl+s", "switch_mode('settings')", "Settings"),
                ("ctrl+h", "switch_mode('help')", "Help")]
    MODES = {
        "meshchat": MainChatScreen,
        "settings": RadioSettingsScreen,
        "help": HelpScreen,
    }


    def __init__(self, radio_path: str):
        super().__init__()
        self.radio_path = radio_path
        pub.subscribe(self.recv_text, "meshtastic.receive.text")
        pub.subscribe(self.on_local_connection, "meshtastic.connection.established")
        self.interface = meshtastic.serial_interface.SerialInterface(devPath=self.radio_path)


    def on_mount(self) -> None:
        self.switch_mode("meshchat")

    def action_request_quit(self) -> None:
        """Action to display the quit dialog."""

        def check_quit(quit: bool) -> None:
            """Called when QuitScreen is dismissed."""
            if quit:
                self.exit()

        self.push_screen(QuitScreen(), check_quit)

    def on_local_connection(self, interface):
        """
        Called when a new radio connection is made
        """
        self.console.print(type(interface))

    def recv_text(self, packet, interface):
        try:
            text_log = self.query_one(RichLog)
            text_log.write(f"{success_green} Incoming Message: {packet}")
            text_log.write(f"{success_green} self.interface Information: {self.interface}")
        except NoMatches as e:
            pass
        # self.console.print(f"{success_green} Incoming Message: {packet}")
        # self.console.print(f"{success_green} self.interface Information: {self.interface}")
        # self.console.print("-----------------")

    # def on_ready(self) -> None:
    #     text_log = self.query_one(RichLog)
    #     self.console.print(text_log)
    #     text_log.write(Syntax(CODE, "python", indent_guides=True))

    # def on_key(self, event: events.Key) -> None:
    #     """Write Key events to log."""
    #     # IF the RichLog exists, use it. else just skip it
    #     try:
    #         text_log = self.query_one(RichLog)
    #         text_log.write(event)
    #     except NoMatches as e:
    #         pass


@click.command("meshChat")
@click.option("-r", "--radio", help="Local path to the radio", default="/dev/ttyACM0", show_default=True,
              type=click.Path(exists=True, readable=True, writable=True, resolve_path=True, allow_dash=True))
@click.pass_context
def main(ctx, radio):
    # console = Console()

    # Grab the radio from the path provided and error checked earlier
    # global interface
    # interface = meshtastic.serial_interface.SerialInterface(devPath=radio)

    # Define the app
    # radio_path
    app = meshChatApp(radio_path=radio)
    app.run()

    # Connect to the radio
    # setup = Setup(console=console,
    # radio_path=radio)
    #
    # pub.subscribe(app.recv_text, "meshtastic.receive.text")
    # Run the app. Do not pass this line until the TUI quits

    # Connect to the radio
    # setup = Setup(console=console, radio_path=radio)
    # Instantiate Parser class
    # parser = Parser(console=console)
    #
    # # Example code for publisher subscribe methods.
    # pub.subscribe(parser.recv_text, "meshtastic.receive.text")
    # pub.subscribe(parser.connection_lost, "meshtastic.connection.lost")
    # pub.subscribe(parser.onConnection, "meshtastic.connection.established")


    # console.print(f"{info_green_splat} Hopefully listening to {radio}")
    # with console.status("Waiting for incoming messages", spinner="dots") as spin:
    #     # Keep the spinner going while messages show up and are printed to screen
    #     while True:
    #         pass






if __name__ == "__main__":
    main()