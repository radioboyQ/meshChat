# Standard library imports
import logging
from pathlib import Path
from pprint import pprint
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

# Import custom status symbols
from meshChatLib import (info_blue_splat,
                         info_green_splat,
                         warning_fmt,
                         prompt_yellow_question,
                         error_fmt,
                         success_green,
                         warning_triangle_yellow)

from meshChatLib.utils import MeshChatUtils, NodeParser, Message, TextMsg, TelemetryMsg, AdminMsg
from meshChatLib.meshScreens import MainChatScreen, QuitScreen, PollingForRadioScreen

# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', port=8080, stdoutToServer=True, stderrToServer=True, suspend=False)

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

    def __init__(self, radio_path: str, pickle_path: Path, reset_node_db: bool = False,
                 db_in_memory: bool = False) -> None:
        super().__init__()
        console = Console()
        logger = logging.getLogger()
        logger.setLevel(logging.ERROR)
        self.radio_path = Path(radio_path)
        self.db_path = Path(pickle_path)
        # A list of rx message dates to be used for text_rx to print line Rules reliably
        # Create a ----- <Jan 1, 1970 ------ type break up for each day messages are received
        # This will need to be tracked per node & per channel
        self.dates_printed = list()
        # Selected DM conversation
        # Default to 0
        self.selected_dm_index = 0

        # Create utils instance
        self.utils = MeshChatUtils(pickle_path=pickle_path)


        # Dictionary to store which option has which node for the sidebar node optionlist
        # Recreate the list on each call of this function, so it's always up-to-date
        # Use the radio ID to identify each node
        self.node_option_list = list()

        ### Set up Meshtastic radio ###
        pub.subscribe(self.rx_packet, "meshtastic.receive.text")
        pub.subscribe(self.on_local_connection, "meshtastic.connection.established")
        pub.subscribe(self.update_nodes, "meshtastic.node.updated")
        pub.subscribe(self.disconnect_radio, "meshtastic.connection.lost")
        # The rest of Meshtastic setup happens in on_ready
        # --- Meshtastic ---
        # return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        text_log = self.query_one(RichLog)
        # Temporary add button on the main screen
        if event.button.id == "add_node":
            # self.notify("Button Pushed", title="Guess what!")

            text_log.write("Btn")
            self.node_listview_table_update()
            text_log.write(self.utils.msg_log_dict)
        else:
            text_log.write(f"Unknown Button Pressed. ID: {event.button.id}")

    def load_chat_log(self, chat_index: int) -> None:
        text_log = self.query_one(RichLog)

        node_id = self.node_option_list[chat_index]
        # Clear screen
        text_log.clear()
        if node_id is None:
            text_log.write(f"No chat for this node.")
        else:
            chat_log_raw = self.utils.get_dms(radio_id=node_id)
            text_log.write(f"{chat_log_raw}")


    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        text_log = self.query_one(RichLog)
        text_log.clear()
        self.load_chat_log(chat_index=event.option_index)
        # Save which node is selected
        self.selected_dm_index = event.option_index


    def on_mount(self) -> None:
        self.switch_mode("meshchat")

    def action_request_quit(self) -> None:
        """Action to display the quit dialog."""

        def check_quit(quit: bool) -> None:
            """Called when QuitScreen is dismissed."""
            if quit:
                # self.interface.close()
                self.exit(result=0)

        self.push_screen(QuitScreen(), check_quit)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Input box for main chat window
        if event.input.id == "main_chat_text_input":
            msg_string = event.value.strip()
            text_log = self.query_one(RichLog)

            text_log.write(f"{self.utils.status_time_prefix}[white bold]|[/][red bold] "
                           f"{self.interface.getLongName()} [/][white bold]>[/] {msg_string}")
            local_radio_id = self.interface.getMyUser()["id"]




            # Everything is DM for now until channels get sorted out
            self.utils.record_dm_msg(sender_id=local_radio_id, receiver_id=self.node_option_list[self.selected_dm_index],
                                     msg=msg_string)



            # Clear the text box after entry
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

        # Set the current chat channel to the local radio, position 0
        self.node_selected_index = 0

    def disconnect_radio(self, interface):
        """
        Called when a radio disconnect event is received.
        Quit and print to console
        """
        self.exit(result=1)

    def update_nodes(self, node, interface):
        text_log = self.query_one(RichLog)
        # text_log.write(f"Update Nodes")
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
                            text_log.write(node_db.get(node_id))
                            # Convert from epoch time to datetime
                            if "lastHeard" not in node_db[node_id]:
                                lastHeard_dt = "Recently"
                            else:
                                lastHeard_dt = datetime.datetime.fromtimestamp(node_db.get(node_id).get("lastHeard"))
                                lastHeard_dt = self.utils.convert_short_datetime(lastHeard_dt).humanize()
                            node_listview_table.add_row(user_dict.get("longName"),
                                                        user_dict.get("shortName"),
                                                        lastHeard_dt)
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

        node_db = self.interface.nodes
        sender_longName = self.interface.nodesByNum[txt_msg.from_radio_num]["user"]["longName"]
        # Check if the selected node is the same node that sent the text
        selected_radio_id = self.node_option_list[self.selected_dm_index]
        if txt_msg.from_radio_id == selected_radio_id:
            # The selected radio and the sender are the same, print the message
            text_log.write(self.utils.text_msg_for_printing(receiver=sender_longName, text_msg=txt_msg.text,
                                                            rx_dt=txt_msg.rx_time))
        else:
            # Do something else if the radio isn't selected. Maybe pop a notification?
            self.notify(message=f"New message from {sender_longName}")
        # Everything is DM for now until channels get sorted out
        self.utils.record_dm_msg(sender_id=txt_msg.from_radio_id, receiver_id=txt_msg.to_radio_id, msg=txt_msg.text)
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
@click.option("--database", "-d", help="Path to the database(pickle) file. Database stores messages in chats",
              default="./meshLibTest.pickle",
              type=click.Path(exists=False, file_okay=True, dir_okay=False, readable=True, writable=True,
                              resolve_path=True), show_default=True)
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
            app = meshChatApp(radio_path=radio, pickle_path=Path(database), reset_node_db=reset_node_db,
                              db_in_memory=db_in_memory)
            exit_code = app.run()
            console.print(f"Exit Code: {exit_code}")
            console.print(f"{exit_code}")
            if exit_code != 0 or exit_code == None:
                start_bool = radio_check(radio_path=radio_path, console=console)
            else:
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
