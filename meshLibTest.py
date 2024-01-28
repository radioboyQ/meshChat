# Standard library imports
from pprint import pprint
import sys
from time import strftime, localtime

# Installed 3rd party modules
import click
import datetime
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from rich import box, inspect
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from textual.app import App, ComposeResult, RenderResult
from textual.containers import ScrollableContainer, Container, VerticalScroll, Vertical, Grid
from textual import events
from textual.css.query import NoMatches
from textual.screen import Screen, ModalScreen
from textual.widget import Widget
from textual.widgets import (Header, Footer, Log, Placeholder, Static, Label, Button, LoadingIndicator, TextArea,
                             Markdown, RichLog, Input, ListView, ListItem, OptionList)

# Import custom status symbols
from meshChatLib import (info_blue_splat,
                       info_green_splat,
                       warning_fmt,
                       prompt_yellow_question,
                       error_fmt,
                       success_green,
                       warning_triangle_yellow)
from meshChatLib.setup import Setup
from meshChatLib.parser import Parser

Base = declarative_base()
engine = create_engine('sqlite:////home/quincy/PycharmProjects/meshChat/meshLibTest.db')

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

# class Node(Widget):
#
#     def compose(self) -> ComposeResult:
#         pass



class MainChatScreen(Screen):

    BINDINGS = [("ctrl+d", "toggle_dark", "Dark Mode"),
                ("ctrl+q", "request_quit", "Quit"),
                ("ctrl+h", "switch_mode('help')", "Help"),
                ("ctrl+s", "switch_mode('settings')", "Settings")]

    def __init__(
            self,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,):
        super().__init__(name, id, classes)


    def compose(self) -> ComposeResult:
        yield Vertical(
                ListView(classes="nodes", id="nodes"),
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



class RadioSettingsScreen(Screen):
    BINDINGS = [("ctrl+d", "toggle_dark", "Dark Mode"),
                ("ctrl+q", "request_quit", "Quit"),
                ("ctrl+t", "switch_mode('meshchat')", "meshChat"),
                ("ctrl+h", "switch_mode('help')", "Help")]

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

    BINDINGS = [("ctrl+d", "toggle_dark", "Dark Mode"),
                ("ctrl+q", "request_quit", "Quit"),
                ("ctrl+t", "switch_mode('meshchat')", "meshChat"),
                ("ctrl+s", "switch_mode('settings')", "Settings")]

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
                ("ctrl+s", "switch_mode('settings')", "Settings"),
                ("ctrl+h", "switch_mode('help')", "Help")]
    MODES = {
        "meshchat": MainChatScreen,
        "settings": RadioSettingsScreen,
        "help": HelpScreen,
    }

    @property
    def status_time_prefix(self):
        # Date time msg received
        now = datetime.datetime.now()
        now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
        # Ljust is to make the formatting look better
        msg_string = f"{now_fmt.ljust(20, ' ')} [white bold]|[/]"
        return msg_string


    def __init__(self, radio_path: str, database_path: str) -> None:
        super().__init__()
        # Set up SQL session before setting up the Meshtastic callbacks
        # Global SQLAlchemy import
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()
        self.session = session

        # Make radio_path avaiable
        self.radio_path = radio_path

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Input box for main chat window
        if event.input.id == "main_chat_text_input":
            msg_string = event.value.strip()
            text_log = self.query_one(RichLog)
            text_log.write(msg_string)
            input_box = self.query_one(Input)
            input_box.clear()
            # Add the message to the SQL DB

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Temporary add button on the main screen
        if event.button.id == "add_node":
            # node_listview = self.query_one("#nodes", ListView)
            # #
            # node_listview.mount(OptionList(*[self.colony(*row) for row in self.COLONIES]))
            # self.notify("Button Pushed", title="Guess what!")
            text_log = self.query_one(RichLog)
            text_log.write("Btn")

    def on_ready(self):
        # Set up call backs
        pub.subscribe(self.recv_text, "meshtastic.receive.text")
        pub.subscribe(self.on_local_connection, "meshtastic.connection.established")
        pub.subscribe(self.update_nodes, "meshtastic.node.updated")
        pub.subscribe(self.disconnect_radio, "meshtastic.connection.lost")
        self.interface = meshtastic.serial_interface.SerialInterface(devPath=self.radio_path)
        # Local radio information
        self.getMyUser = self.interface.getMyUser()
        text_log = self.query_one(RichLog)

        # Grabbing the local radio's information
        # text_log.write(self.session)
        # text_log.write(f"Local radio: {self.getMyUser}")

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
        try:
            text_log = self.query_one(RichLog)
        except NoMatches as e:
            pass
        # text_log.write(inspect(interface))

    def recv_text(self, packet, interface):
        try:
            text_log = self.query_one(RichLog)
            # text_log.write(f"{success_green} Incoming Message: {packet}")
            # text_log.write(f"{success_green} self.interface Information: {self.interface}")
            decoded_text = packet.get("decoded").get('text')
            # Date time msg received
            now = datetime.datetime.now()
            now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
            # Ljust is to make the formatting look better
            msg_string = f"{now_fmt.ljust(20, ' ')} [white bold]|[/] {decoded_text}"
            text_log.write(msg_string)
        except NoMatches as e:
            pass

    def disconnect_radio(self, interface):
        """
        Called when a radio disconnect event is received.
        Quit and print to console
        """
        text_log = self.query_one(RichLog)
        text_log.write(f"{self.status_time_prefix} Radio Disconnect")


        self.exit()

    def update_nodes(self, node, interface):
        try:
            text_log = self.query_one(RichLog)
            # Check if the node has been seen before
            query_records = self.session.query(Node).filter_by(macaddr=node.get("user").get("macaddr"))

            all_nodes = self.session.query(Node).all()
            for node in all_nodes:
                text_log.write(f"{node.macaddr} node")
            text_log.write("-------")




            if query_records.count() == 1:
                # There's only one
                for i in query_records:
                    text_log.write((f"There's only one"))

                    text_log.write(i.longName)
                    node_listview = self.query_one("#nodes", ListView)
                    # Create the table for the sidebar
                    """
                    Long Name
                    Short Name
                    Last Seen"""



                    # node_listview.mount(OptionList())

                    # Update sidebar
                    new_node = Node(longName=node.get("user").get("longName"),
                                    shortName=node.get("user").get("shortName"),
                                    macaddr=node.get("user").get("macaddr"),
                                    hwModel=node.get("user").get("hwModel"))
                    self.session.add(new_node)
                    self.session.commit()
                    all_nodes = self.session.query(Node).all()
                    node_list = self.query_one("#nodes")
                    text_log.write(type(node_list))
                    # Update sidebar
                    for node in all_nodes:
                        node_listview = self.query_one("#nodes", ListView)
                    # node_listview.mount(OptionList(*[self.colony(*row) for row in self.COLONIES]))
                    text_log.write("Update Nodes List")
                    text_log.write(node)
                    # text_log.write(all_nodes)
                    text_log.write("Interface")
                    text_log.write(interface)

            elif query_records.count() == 0:
                # If node not seen before, add to DB

                new_node = Node(longName=node.get("user").get("longName"),
                                shortName=node.get("user").get("shortName"),
                                macaddr=node.get("user").get("macaddr"),
                                hwModel=node.get("user").get("hwModel"))
                self.session.add(new_node)
                self.session.commit()
                all_nodes = self.session.query(Node).all()
                # node_listview.mount(OptionList(*[self.colony(*row) for row in self.COLONIES]))

                node_listview = self.query_one("#nodes", ListView)
                text_log.write(type(node_listview))
                # Update sidebar
                for node in all_nodes:
                    node_listview = self.query_one("#nodes", ListView)
                # node_listview.mount(OptionList(*[self.colony(*row) for row in self.COLONIES]))
                text_log.write("Update Nodes List")
                text_log.write(node)
                # text_log.write(all_nodes)
                text_log.write("Interface")
                text_log.write(interface)


            else:
                # There's more than one?
                for record in query_records:
                    text_log.write(f"There's more than one node with that MAC")
                    text_log.write(record)

        except NoMatches as e:
            # pass
            text_log = self.query_one(RichLog)
            text_log.write("Exception")
            text_log.write(e)



            # query = Node.select(macaddr=node.get("user").get("macaddr"))
            # text_log.write(query)

            # text_log.write(self.session.scalars(select(Node).order_by(Node.macaddr)).all())



class Node(Base):
    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    longName = Column(String(50), unique=False, nullable=False)
    shortName = Column(String(10), unique=False, nullable=False)
    macaddr = Column(String(20), unique=True, nullable=False)
    hwModel = Column(String(100), unique=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)



@click.command("meshChat")
@click.option("-r", "--radio", help="Local path to the radio", default="/dev/ttyACM0", show_default=True,
              type=click.Path(exists=True, readable=True, writable=True, resolve_path=True, allow_dash=True))
@click.option("--database", "-d", help="Path to the database file", default="./meshLibTest.db",
              type=click.Path(exists=False, file_okay=True, dir_okay=False, readable=True, writable=True, resolve_path=True),
              show_default=True)
@click.pass_context
def main(ctx, radio, database):
    # console = Console()

    # Define the app
    app = meshChatApp(radio_path=radio,database_path=database)
    app.run()

if __name__ == "__main__":
    main()