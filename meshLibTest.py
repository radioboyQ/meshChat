# Standard library imports
import logging
from pathlib import Path
from pprint import pprint
import sqlite3
import sys
from time import strftime, localtime, sleep

# Installed 3rd party modules
import arrow
import click
import datetime
import meshtastic
from meshtastic.serial_interface import SerialInterface
from pubsub import pub
from rich import box, inspect
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, ProgressColumn, TimeElapsedColumn, BarColumn, \
    MofNCompleteColumn
from rich.syntax import Syntax
from rich.table import Table
from textual import events, work
from textual.app import App, ComposeResult, RenderResult
from textual.containers import ScrollableContainer, Container, VerticalScroll, Vertical, Grid, Center, Middle
from textual.css.query import NoMatches
from textual.screen import Screen, ModalScreen
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import (Header, Footer, Log, Placeholder, Static, Label, Button, LoadingIndicator, TextArea,
                             Markdown, RichLog, Input, ListView, ListItem, OptionList, ProgressBar)
from textual.worker import Worker, get_current_worker

import meshChatLib.utils
# Import custom status symbols
from meshChatLib import (info_blue_splat,
                         info_green_splat,
                         warning_fmt,
                         prompt_yellow_question,
                         error_fmt,
                         success_green,
                         warning_triangle_yellow)

from meshChatLib.utils import MeshtasticUtils, NodeParser, Message, TextMsg, TelemetryMsg, AdminMsg
from meshChatLib.meshScreens import MainChatScreen, QuitScreen, PollingForRadioScreen

class meshChatApp(App):
    """Starting meshChat client"""
    TITLE = "meshChat"
    SUB_TITLE = "The finest off grid chat application"
    CSS_PATH = "meshChatLib/meshLibTest.tcss"

    BINDINGS = [
        ("ctrl+d", "toggle_dark", "Dark Mode"),
        ("ctrl+q", "request_quit", "Quit"),
    ]

    MODES = {
        "meshchat": MainChatScreen,
    }

    def __init__(self, radio_path: str, database_path: str, reset_node_db: bool = False,
                 db_in_memory: bool = False) -> None:
        super().__init__()
        console = Console()
        logger = logging.getLogger()
        logger.setLevel(logging.ERROR)
        self.radio_path = Path(radio_path)
        self.db_path = Path(database_path)
        # A list of rx message dates to be used for text_rx to print line Rules reliably
        self.dates_printed = list()

        ### Set up database###
        # reset_node_db True: drop all tables and reset the radio's nodeDB to start fresh
        self.reset_node_db = reset_node_db

        if db_in_memory:
            self.connection = sqlite3.connect(":memory:")
            # self.engine = create_engine(":memory:", echo=False, future=True)
        else:
            self.connection = sqlite3.connect(f"{self.db_path}")
            # self.engine = create_engine(f"{self.db_path}", echo=False)

        # Dictionary to store which option has which node for the sidebar node optionlist
        # Recreate the list on each call of this function, so it's always up-to-date
        # Use the radio ID to identify each node
        self.node_option_list = list()

        # --- Database ---
        ### Set up Meshtastic radio ###
        pub.subscribe(self.rx_packet, "meshtastic.receive.text")
        pub.subscribe(self.on_local_connection, "meshtastic.connection.established")
        pub.subscribe(self.update_nodes, "meshtastic.node.updated")
        # pub.subscribe(self.disconnect_radio, "meshtastic.connection.lost")
        # The rest of Meshtastic setup happens in on_ready
        # --- Meshtastic ---
        return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        text_log = self.query_one(RichLog)
        # Temporary add button on the main screen
        if event.button.id == "add_node":
            # node_listview = self.query_one("#nodes", ListView)
            # #
            # node_listview.mount(OptionList(*[self.colony(*row) for row in self.COLONIES]))
            # self.notify("Button Pushed", title="Guess what!")

            text_log.write("Btn")
            self.node_listview_table_update()
        else:
            text_log.write(f"Unknown Button Pressed. ID: {event.button.id}")

    def on_mount(self) -> None:
        self.switch_mode("meshchat")

    def action_request_quit(self) -> None:
        """Action to display the quit dialog."""

        def check_quit(quit: bool) -> None:
            """Called when QuitScreen is dismissed."""
            if quit:
                self.exit(result=0)

        self.push_screen(QuitScreen(), check_quit)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Input box for main chat window
        if event.input.id == "main_chat_text_input":
            msg_string = event.value.strip()
            text_log = self.query_one(RichLog)
            text_log.write(self.interface.getLongName())
            text_log.write(f"{meshChatLib.utils.Utils().status_time_prefix}[white bold]|[/][red bold] "
                           f"{self.interface.getLongName()} [/][white bold]>[/] {msg_string}")
            input_box = self.query_one(Input)
            input_box.clear()

    def on_local_connection(self, interface):
        text_log = self.query_one(RichLog)
        text_log.write(f"Connected to the radio")
        # Start Meshtatic interface when the UI is ready
        if not hasattr(self, 'interface'):
            self.interface = meshtastic.serial_interface.SerialInterface(devPath=str(self.radio_path))

    def on_ready(self):

        # Start Meshtatic interface when the UI is ready
        self.interface = meshtastic.serial_interface.SerialInterface(devPath=str(self.radio_path))

        # Update the sidebar
        self.node_listview_table_update()

    def update_nodes(self, node, interface):
        text_log = self.query_one(RichLog)
        text_log.write(f"Update Nodes")
        # interface isn't created until on_ready is called
        if hasattr(self, 'interface'):
            self.node_listview_table_update()

    def node_listview_table_update(self):
        text_log = self.query_one(RichLog)
        node_option_list = self.query_one("#nodes", OptionList)
        # Query all the nodes from Meshtastic
        if hasattr(self, 'interface'):
            # Local node information
            local_node = self.interface.getMyUser()
            node_db = self.interface.nodes
            for node_id in node_db:
                if node_id in self.node_option_list:
                    # text_log.write(f"Skipping adding RID {node_id}, it exists in the list already")
                    pass
                else:
                    # Set up table for sidebar, new for each radio
                    node_listview_table = Table()
                    node_listview_table.add_column("LongName")
                    node_listview_table.add_column("ShortName")
                    node_listview_table.add_column("LastSeen")
                    # Easy to get user dict
                    user_dict = node_db.get(node_id).get("user")
                    # If the local node ID matches the iterating node from the DB ID
                    if local_node.get("id") == node_id:
                        # text_log.write(node_db.get(node_id))
                        node_listview_table.add_row(user_dict.get("longName"), user_dict.get("shortName"), f"Local Node")

                    else:
                        # text_log.write(node_db.get(node_id))
                        if "lastHeard" in node_db.get(node_id):
                            # Convert from epoch time to datetime
                            lastHeard_dt = datetime.datetime.fromtimestamp(node_db.get(node_id).get("lastHeard"))
                            node_listview_table.add_row(user_dict.get("longName"),
                                                        user_dict.get("shortName"),
                                                        self.convert_short_datetime(lastHeard_dt).humanize())
                        else:
                            node_listview_table.add_row(user_dict.get("longName"),
                                                        user_dict.get("shortName"), "Unknown")
                    node_option_list.add_option(node_listview_table)
                    self.node_option_list.append(node_id)

    def text_rx(self, txt_msg: TextMsg):
        """
        Called for text messages
        - Parse the message into :TextMsg
        - Look up the radioId
        - Put the message into the database
        - Render the message to screen
        """
        text_log = self.query_one(RichLog)

        from_node_id = txt_msg.from_radio_id

        node_db = self.interface.nodes
        user_dict = node_db.get(from_node_id).get("user")
        text_log.write(
            f"{meshChatLib.utils.Utils().status_time_prefix}[white bold]|[/][red bold] {user_dict.get('longName')} [/][white bold]>[/] {txt_msg.text}")
        if hasattr(self, 'interface'):
            self.node_listview_table_update()

    def rx_packet(self, packet, interface):
        """
        Called when any packet is received from Meshtastic
        """

        text_log = self.query_one(RichLog)

        port_num_str = packet.get("decoded").get("portnum")

        if port_num_str == "ADMIN_APP":
            # This is an admin function
            pass
            # console.print(f"Admin")
            # console.print(f"{packet}")

        elif port_num_str == "POSITION_APP":
            # GPS data
            position_app = True
        elif port_num_str == "TEXT_MESSAGE_APP":
            # Text message
            txt = TextMsg(raw_msg=packet)
            self.text_rx(txt_msg=txt)


        elif port_num_str == "TELEMETRY_APP":
            # console.print(packet)
            tel = TelemetryMsg(raw_msg=packet)
            # console.print(tel.from_radio_num)

        # Date time msg received
        now = datetime.datetime.now()
        now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
        # Ljust is to make the formatting look better
        # msg_string = f"{now_fmt.ljust(20, ' ')} [white bold]|[/] {decoded_text}"
        # text_log.write(msg_string)
        # Update the view
        self.node_listview_table_update()


    def convert_short_datetime(self, datetime_obj: datetime.datetime):
        """
        Take in a date time object and convert it to "Minutes ago", "Hours ago", etc
        """
        now_fmt = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

        a_time = arrow.get(now_fmt)
        return a_time

def radio_check(radio_path: Path, console: Console):
    timeout = 30  # Time to wait in seconds
    console.clear()
    start_time = datetime.datetime.now()

    with Progress(BarColumn(), TextColumn(text_format="{task.description}"), MofNCompleteColumn(),
                  TextColumn(text_format="seconds"), transient=True, console=console, expand=False) as prog:
        prog_task = prog.add_task(f"Checking for radio at [magenta][bold]{radio_path}[/] for", total=timeout)
        time_since_start = datetime.datetime.now() - start_time

        # Check to see if the provided path has anything.
        # There is no checking to ensure if it's a meshtastic radio outside Meshtastic API
        while time_since_start.seconds < timeout and not radio_path.exists():
            time_since_start = datetime.datetime.now() - start_time
            advance_time_incriment = 0.3
            prog.update(prog_task, advance=advance_time_incriment)
            sleep(advance_time_incriment)
        if not time_since_start.seconds < timeout:
            console.log(f"{error_fmt} Radio not found at {radio_path} in {timeout} seconds")
            console.log(f"{success_green} Plug in a radio and start this again or try [code]--help")
            sys.exit(1)

@click.command("meshChat")
@click.option("-r", "--radio", help="Local path to the radio", default="/dev/ttyACM0", show_default=True,
              type=click.Path(exists=False, readable=True, writable=True, resolve_path=True, allow_dash=True))
@click.option("--database", "-d", help="Path to the database file", default="./meshLibTest.db",
              type=click.Path(exists=False, file_okay=True, dir_okay=False, readable=True, writable=True,
                              resolve_path=True),
              show_default=True)
@click.option("-m", "--db-in-memory", is_flag=True, default=False, show_default=True,
              help="Store the database in memory. Supersedes --database option.")
@click.option("--reset_node_db", help="Reset node database", is_flag=True, default=False, show_default=True)
@click.pass_context
def main(ctx, radio, database, reset_node_db, db_in_memory):
    console = Console()
    radio_path = Path(radio)
    # Check if the radio exists, if not poll for it
    while True:
        if radio_path.exists():
            app = meshChatApp(radio_path=radio, database_path=database, reset_node_db=reset_node_db,
                              db_in_memory=db_in_memory)
            exit_code = app.run()
            console.print(f"Exit Code: {exit_code}")
            console.print(f"{exit_code}")
            sys.exit(0)
            # if exit_code != 0 or exit_code == None:
            #     if exit_code == 1:
            #         exit_msg = f"radio disconnected"
            #         console.log(f"{error_fmt} Something went wrong: {exit_msg}")
            # else:

        else:
            start_bool = radio_check(radio_path=radio_path, console=console)


if __name__ == "__main__":
    main()
