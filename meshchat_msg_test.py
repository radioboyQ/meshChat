import logging
from pathlib import Path
from pprint import pprint
import sys
from time import strftime, localtime, sleep

# Installed 3rd party modules
import click
import datetime
import meshtastic
from meshtastic import admin_pb2
from meshtastic.serial_interface import SerialInterface
from pubsub import pub
from rich import box, inspect
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, ProgressColumn, TimeElapsedColumn, BarColumn, \
    MofNCompleteColumn
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean, update, insert, select, \
    MetaData, Float
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

console = Console()

logger = logging.getLogger()
logger.setLevel(logging.ERROR)


def main():
    radio_path = "/dev/ttyACM0"
    Path(radio_path)
    pub.subscribe(recv_text, "meshtastic.receive")
    interface = meshtastic.serial_interface.SerialInterface(devPath=str(radio_path))

    with Status(f"Waiting on a message with {radio_path}", console=console) as status:
        # console.print(interface.getMyUser())
        node = meshtastic.node.Node(interface, interface.getMyUser().get("id"))
        console.print(node.getMetadata())
        channelNum = 0
        p = admin_pb2.AdminMessage()
        p.get_channel_request = channelNum + 1
        node._sendAdmin(
            p, wantResponse=True, onResponse=onResponseRequestChannel
        )
        # while True:
        #     pass


class Utils(object):

    def __init__(self, radio_path: Path, interface: SerialInterface) -> None:
        self.radio_path = radio_path
        self.radio_interface = interface

    def get_local_config(self) -> dict:
        """
        Request the current configuration of the radio
        """

    @property
    def status_time_prefix(self):
        # Date time msg received
        now = datetime.datetime.now()
        now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
        # Ljust is to make the formatting look better
        msg_string = f"{now_fmt.ljust(20, ' ')}"
        return msg_string


def onResponseRequestChannel(p):
    console.print("onResponseRequestChannel", p)


def recv_text(packet, interface):
    console.print('[blue bold]-' * 10)

    console.print('[purple bold]-' * 10)
    port_num_str = packet.get("decoded").get("portnum")

    if port_num_str == "ADMIN_APP":
        # This is an admin function
        pass
        console.print(f"Admin")
        console.print(f"{packet}")

    elif port_num_str == "POSITION_APP":
        # GPS data
        console.print(f"Position")
    elif port_num_str == "TEXT_MESSAGE_APP":
        # Text message
        console.print(f"Text message")
        console.print(packet)
        # txt = TextMsg(raw_msg=packet)
        # console.print(f"From: {txt.from_radio_id}")
        # console.print(f"To: {txt.to_radio_id}")
        # console.print(f"Body: {txt.text}")

    elif port_num_str == "TELEMETRY_APP":
        console.print("Telemetery")
        tel = TelemetryMsg(raw_msg=packet)
        # console.print(tel.from_radio_id)
        console.print(interface.getNode(nodeId=tel.from_radio_id))
        # console.print(tel.from_radio_num)
    elif port_num_str == "ROUTING_APP":

        console.print(f"Routing")


    else:
        console.print(packet)


class Message(object):

    def __init__(self, raw_msg: dict):
        """Base class for all messages"""
        self._raw_msg = raw_msg

    @property
    def rx_time(self):
        return self._raw_msg.get("rx_time")

    @property
    def hopLimit(self):
        return self._raw_msg.get("hopLimit")

    @property
    def priority(self):
        return self._raw_msg.get("priority")

    @property
    def msg_id(self):
        return self._raw_msg.get("id")

    @property
    def portnum(self):
        return self._raw_msg.get("decoded").get("portnum")

    @property
    def payload(self):
        return self._raw_msg.get("decoded").get("payload")

    @property
    def from_radio_id(self):
        return self._raw_msg.get("fromId")

    @property
    def to_radio_id(self):
        return self._raw_msg.get("toId")

    @property
    def from_radio_num(self):
        return self._raw_msg.get("from")

    @property
    def to_radio_num(self):
        return self._raw_msg.get("to_radio_num")


class AdminMsg(Message):

    def __init__(self, raw_msg: dict):
        self._raw_msg = raw_msg


class TextMsg(Message):

    def __init__(self, raw_msg: dict):
        self._raw_msg = raw_msg

    @property
    def rxSnr(self):
        return self._raw_msg.get("rxSnr")

    @property
    def rxTime(self):
        return self._raw_msg.get("rxTime")

    @property
    def rxRssi(self):
        return self._raw_msg.get("rxRssi")

    @property
    def text(self):
        return self._raw_msg.get("decoded").get("text")


class TelemetryMsg(Message):

    def __init__(self, raw_msg: dict):
        self._raw_msg = raw_msg

    @property
    def from_radio_num(self):
        return self._raw_msg.get("from")

    @property
    def to_radio_num(self):
        return self._raw_msg.get("to_radio_num")

    @property
    def airUtilTx(self):
        return self._raw_msg.get("decoded").get("telemetry").get("deviceMetrics").get("airUtilTx")

    @property
    def timestamp(self):
        return self._raw_msg.get("decoded").get("telemetry").get("time")


if __name__ == "__main__":
    main()