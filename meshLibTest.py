# Standard library imports
import logging
from pathlib import Path
from pprint import pprint
import sys
from time import strftime, localtime, sleep

# Installed 3rd party modules
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
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean, update, insert, select, \
    MetaData, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, registry, DeclarativeBase
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


class Base(DeclarativeBase):
    pass


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
        "radiocheck": PollingForRadioScreen,
    }

    def __init__(self, radio_path: str, database_path: str, reset_node_db: bool = False,
                 db_in_memory: bool = False) -> None:
        super().__init__()
        console = Console()
        logger = logging.getLogger()
        logger.setLevel(logging.ERROR)
        self.radio_path = Path(radio_path)
        self.db_path = Path(database_path)

        ### Set up database###
        # reset_node_db True: drop all tables and reset the radio's nodeDB to start fresh
        self.reset_node_db = reset_node_db

        if db_in_memory:
            self.engine = create_engine("sqlite+pysqlite:///:memory:", echo=False, future=True)
        else:
            self.db_path = self.db_path
            self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        session = Session()
        self.session = session

        # --- Database ---
        ### Set up Meshtastic radio ###
        pub.subscribe(self.rx_packet, "meshtastic.receive.text")
        pub.subscribe(self.on_local_connection, "meshtastic.connection.established")
        pub.subscribe(self.update_nodes, "meshtastic.node.updated")
        pub.subscribe(self.disconnect_radio, "meshtastic.connection.lost")
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
                # Disable the local node on exit
                self.disable_local_radio()
                self.exit(result=0)

        self.push_screen(QuitScreen(), check_quit)

    def on_ready(self):

        # Start Meshtatic interface when the UI is ready
        self.interface = meshtastic.serial_interface.SerialInterface(devPath=str(self.radio_path))

        # Update the node list
        self.node_listview_table_update()

    def on_click(self):
        text_log = self.query_one(RichLog)
        text_log.write(f"Click!")

    def on_option_list_option_selected(self):
        """
        Selected when the user clicks on or hits enter on the keyboard.
        Just highlighting isn't enough
        """
        text_log = self.query_one(RichLog)
        option_list = self.query_one(OptionList)
        if option_list.highlighted <= len(self.node_option_list):
            text_log.write(option_list.get_option_at_index(option_list.highlighted).id)
            node_option_mac = self.node_option_list[option_list.highlighted]
        resp = self.session.query(Node).filter_by(macaddr=node_option_mac)
        for node in resp.all():
            # Get the data for each node here
            # Load the chat
            pass



    def on_local_connection(self, interface):
        text_log = self.query_one(RichLog)
        # text_log.write(f"New local connection")
        self.getMyUser = self.interface.getMyUser()
        self.radio_id = self.getMyUser.get("id")
        self.longName = self.getMyUser.get("longName")
        self.shortName = self.getMyUser.get("shortName")
        self.hwModel = self.getMyUser.get("hwModel")
        self.macaddr = self.getMyUser.get("macaddr")

        select_stmt = select(Node).filter_by(macaddr=self.macaddr)
        resp = self.session.execute(select_stmt)
        if len(resp.fetchall()) == 0:
            # text_log.write(self.interface.getMyUser())
            # Wrap this response inside a dictionary beacuse that's how other respones work
            node_obj = NodeParser({"user": self.interface.getMyUser()})
            local_node = Node(radio_num=node_obj.radio_num, radio_id=node_obj.radio_id, longName=node_obj.longName,
                              shortName=node_obj.shortName, macaddr=node_obj.macaddr, hwModel=node_obj.hwModel,
                              role=node_obj.role, snr=node_obj.snr,
                              lastHeard=node_obj.lastHeard, batteryLevel=node_obj.batteryLevel,
                              voltage=node_obj.voltage, channelUtilization=node_obj.channelUtilization,
                              airUtilTx=node_obj.airUtilTx, latitudeI=node_obj.latitudeI,
                              longitudeI=node_obj.longitudeI, altitude=node_obj.altitude,
                              time=node_obj.time, latitude=node_obj.latitude, longitude=node_obj.longitude)
            # Add node to DB
            self.session.add(local_node)
            self.session.commit()
        else:
            u = update(Node)
            u = u.values({"local_radio": True})
            u = u.where(Node.macaddr == self.macaddr)
            self.session.execute(u)
            self.session.commit()



    def text_rx(self, txt_msg: TextMsg):
        """
        Called for text messages
        - Parse the message into :TextMsg
        - Look up the radioId
        - Put the message into the database
        - Render the message to screen
        """
        text_log = self.query_one(RichLog)
        node_id = txt_msg.from_radio_id
        text_log.write(self.interface.getNode(nodeId=node_id))

        resp = self.session.query(Node).filter_by(radio_id=txt_msg.from_radio_id).all()

        for node in resp:
            text_log.write(f"{meshChatLib.utils.Utils().status_time_prefix}[white bold]|[/][red bold]{node.longName}[/][white bold]>[/] {txt_msg.text}")

            # Add text to database
            new_msg = ChannelHistory(from_radio_id=txt_msg.from_radio_id, to_channel=txt_msg.to_radio_id, msg_text=txt_msg.text)
            self.session.execute(new_msg)
            self.session.commit()




        # text_log.write(f"From: {txt_msg.from_radio_id}")
        # text_log.write(f"To: {txt_msg.to_radio_id}")
        # text_log.write(f"Body: {txt_msg.text}")


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

    def disconnect_radio(self, interface):
        """
        Called when a radio disconnect event is received.
        Quit and print to console
        """

        # Remove local radio from SQL
        self.disable_local_radio()
        self.exit(result=1)

        # if not self.radio_path.exists():
        #     self.radio_disconnect_polling()
        # self.interface = meshtastic.serial_interface.SerialInterface(devPath=str(self.radio_path))

    def update_nodes(self, node, interface):
        text_log = self.query_one(RichLog)
        node_obj = NodeParser(node)

        resp = self.session.query(Node).filter_by(macaddr=node_obj.macaddr)

        if resp.count() == 0:
            new_node = Node(radio_num=node_obj.radio_num, radio_id=node_obj.radio_id, longName=node_obj.longName,
                            shortName=node_obj.shortName, macaddr=node_obj.macaddr, hwModel=node_obj.hwModel,
                            role=node_obj.role, snr=node_obj.snr,
                            lastHeard=node_obj.lastHeard, batteryLevel=node_obj.batteryLevel,
                            voltage=node_obj.voltage, channelUtilization=node_obj.channelUtilization,
                            airUtilTx=node_obj.airUtilTx, latitudeI=node_obj.latitudeI,
                            longitudeI=node_obj.longitudeI, altitude=node_obj.altitude,
                            time=node_obj.time, latitude=node_obj.latitude, longitude=node_obj.longitude)
            self.session.add(new_node)
        else:
            update_stmt = update(Node).filter_by(macaddr=node_obj.macaddr).values(radio_num=node_obj.radio_num, radio_id=node_obj.radio_id, longName=node_obj.longName,
                                                                                  shortName=node_obj.shortName, macaddr=node_obj.macaddr, hwModel=node_obj.hwModel,
                                                                                  role=node_obj.role, snr=node_obj.snr,
                                                                                  lastHeard=node_obj.lastHeard, batteryLevel=node_obj.batteryLevel,
                                                                                  voltage=node_obj.voltage, channelUtilization=node_obj.channelUtilization,
                                                                                  airUtilTx=node_obj.airUtilTx, latitudeI=node_obj.latitudeI,
                                                                                  longitudeI=node_obj.longitudeI, altitude=node_obj.altitude,
                                                                                  time=node_obj.time, latitude=node_obj.latitude, longitude=node_obj.longitude)
            self.session.execute(update_stmt)
        self.session.commit()


    def node_listview_table_update(self):
        # Dictionary to store which option has which node
        # Recreate the list on each call of this function, so it's always up-to-date
        # Use the MAC addr to identify each node
        self.node_option_list = list()

        # text_log = self.query_one(RichLog)
        node_option_list = self.query_one("#nodes", OptionList)
        node_option_list.clear_options()

        # Create the table for the sidebar
        all_nodes_stmt = select(Node)
        result = self.session.execute(all_nodes_stmt).fetchall()
        # query_records = self.session.execute(select(Node).filter_by(macaddr=node.get("user").get("macaddr")))
        # text_log.write(query_records)

        # Need to iterate down twice for each node, not sure why yet.
        for counter, row in enumerate(result):
            for node in row:
                node_listview_table = Table()
                node_listview_table.add_column("LongName")
                node_listview_table.add_column("ShortName")
                node_listview_table.add_column("LastSeen")

                # Mark the local radio instead of last seen time
                if node.local_radio:
                    node_listview_table.add_row(node.longName, node.shortName, f"Local Node")
                else:
                    if node.lastHeard == None:
                        node_last_heard = node.last_seen
                    else:
                        node_last_heard = node.lastHeard
                    node_listview_table.add_row(node.longName, node.shortName,
                                                self.convert_short_datetime(node_last_heard).humanize())
                node_option_list.add_option(node_listview_table)
                self.node_option_list.append(node.macaddr)

    def disable_local_radio(self):
        # Disable the local node on exit
        u = update(Node)
        u = u.values({"local_radio": False})
        u = u.where(Node.local_radio == True)
        self.session.execute(u)
        self.session.commit()
        self.exit()

    def convert_short_datetime(self, datetime_obj: datetime.datetime):
        """
        Take in a date time object and convert it to "Minutes ago", "Hours ago", etc
        """
        import arrow
        now_fmt = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

        a_time = arrow.get(now_fmt)
        return a_time

    # async def update_weather(self) -> None:



# Remove all but the essential data?
# Does the radio cache old data?
# Test request then disconnect far radio and test again
class Node(Base):
    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_seen = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    # Local radio sent per instance
    local_radio = Column(Boolean, default=False)
    # Meshtastic provided information
    radio_num = Column(String(50), unique=False, nullable=True)
    radio_id = Column(String(50), unique=True, nullable=False)
    longName = Column(String(50), unique=False, nullable=False)
    shortName = Column(String(10), unique=False, nullable=False)
    macaddr = Column(String(20), unique=True, nullable=False)
    hwModel = Column(String(100), unique=False, nullable=False)
    role = Column(String(50), unique=False, nullable=True)
    snr = Column(String(50), unique=False, nullable=True)
    # ToDo: Change to datetime see if
    lastHeard = Column(String(50), unique=False, nullable=True)
    batteryLevel = Column(Integer(), unique=False, nullable=True)
    voltage = Column(Float(), unique=False, nullable=True)
    channelUtilization = Column(Float(), unique=False, nullable=True)
    airUtilTx = Column(Float(), unique=False, nullable=True)
    latitudeI = Column(Float(), unique=False, nullable=True)
    longitudeI = Column(Float(), unique=False, nullable=True)
    altitude = Column(Integer(), unique=False, nullable=True)
    time = Column(String(75), unique=False, nullable=True)
    latitude = Column(Float(), unique=False, nullable=True)
    longitude = Column(Float(), unique=False, nullable=True)


class ChannelHistory(Base):
    __tablename__ = 'channel_history'

    id = Column(Integer, primary_key=True)
    from_radio_id = Column(ForeignKey("node.radio_id"), nullable=True)
    to_channel = Column(String(50), nullable=True)
    msg_text = Column(String(50), nullable=False)
    time_rx = Column(DateTime(timezone=True), default=func.run())
    # FROM Radio ID as a foregin key
    # TO channel/DM
    # Message text
    # DateTime RX


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
            app = meshChatApp(radio_path=radio, database_path=database, reset_node_db=reset_node_db, db_in_memory=db_in_memory)
            exit_code = app.run()
            console.print(f"Exit Code: {exit_code}")
            # if exit_code != 0 or exit_code == None:
            #     if exit_code == 1:
            #         exit_msg = f"radio disconnected"
            #         console.log(f"{error_fmt} Something went wrong: {exit_msg}")
            # else:
            sys.exit(0)

        else:
            start_bool = radio_check(radio_path=radio_path, console=console)


if __name__ == "__main__":
    main()
