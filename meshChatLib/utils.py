# Standard library imports
import datetime
from pathlib import Path
from pprint import pprint
import sys
from time import strftime, localtime, sleep

import meshtastic
from meshtastic.serial_interface import SerialInterface
from pubsub import pub
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean, update, insert, select
from sqlalchemy.orm import Session


class Utils(object):

    @property
    def status_time_prefix(self):
        # Date time msg received
        now = datetime.datetime.now()
        now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
        # Ljust is to make the formatting look better
        msg_string = f"{now_fmt.ljust(20, ' ')}"
        return msg_string


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


class Channel(object):

    def __init__(self, txt_msg: TextMsg):
        self._txt_msg = txt_msg

class DirectMessage(object):

    def __init__(self, txt_msg: TextMsg):
        self._txt_msg = txt_msg

class Routing(Message):

    def __init__(self, raw_msg: dict):
        self._raw_msg = raw_msg

    @property
    def errorReason(self) -> None:
        if self._raw_msg.get("decoded") and self._raw_msg.get("decoded").get("routing") and self._raw_msg.get("decoded").get("routing").get("errorReason"):
            return self._raw_msg.get("decoded").get("routing").get("errorReason")
        else:
            return None

class NodeParser(object):
    def __init__(self, node):
        self.node = node

    @property
    def radio_num(self):
        if self.node.get("num"):
            return self.node.get("num")
        else:
            return None
    @property
    def radio_id(self):
        if self.node.get("user") and self.node.get("user").get("id"):
            return self.node.get("user").get("id")
        else:
            return None
    @property
    def longName(self):
        if self.node.get("user") and self.node.get("user").get("longName"):
            return self.node.get("user").get("longName")
        else:
            return None
    @property
    def shortName(self):
        if self.node.get("user") and self.node.get("user").get("shortName"):
            return self.node.get("user").get("shortName")
        else:
            return None
    @property
    def macaddr(self):
        if self.node.get("user") and self.node.get("user").get("macaddr"):
            return self.node.get("user").get("macaddr")
        else:
            return None
    @property
    def hwModel(self):
        if self.node.get("user") and self.node.get("user").get("hwModel"):
            return self.node.get("user").get("hwModel")
        else:
            return None
    @property
    def role(self):
        if self.node.get("user") and self.node.get("user").get("role"):
            return self.node.get("user").get("role")
        else:
            return None
    @property
    def snr(self):
        if self.node.get("snr"):
            self.node.get("snr")
        else:
            return None
    @property
    def lastHeard(self):
        if self.node.get("lastHeard"):
            self.node.get("lastHeard")
        else:
            return None
    @property
    def batteryLevel(self):
        if self.node.get("deviceMetrics") and self.node.get("deviceMetrics").get("batteryLevel"):
            self.node.get("deviceMetrics").get("batteryLevel")
        else:
            return None
    @property
    def voltage(self):
        if self.node.get("deviceMetrics") and self.node.get("deviceMetrics").get("voltage"):
            self.node.get("deviceMetrics").get("voltage")
        else:
            return None

    @property
    def channelUtilization(self):
        if self.node.get("deviceMetrics") and self.node.get("deviceMetrics").get("channelUtilization"):
            self.node.get("deviceMetrics").get("channelUtilization")
        else:
            return None
    @property
    def airUtilTx(self):
        if self.node.get("deviceMetrics") and self.node.get("deviceMetrics").get("airUtilTx"):
            return self.node.get("deviceMetrics").get("airUtilTx")
        else:
            return None
    @property
    def latitudeI(self):
        if self.node.get("position") and self.node.get("position").get("latitudeI"):
            return self.node.get("position").get("latitudeI")
        else:
            return None
    @property
    def longitudeI(self):
        if self.node.get("position") and self.node.get("position").get("longitudeI"):
            return self.node.get("position").get("longitudeI")
        else:
            return None

    @property
    def altitude(self):
        if self.node.get("position") and self.node.get("position").get("altitude"):
            return self.node.get("position").get("altitude")
        else:
            return None
    @property
    def time(self):
        if self.node.get("position") and self.node.get("position").get("time"):
            return self.node.get("position").get("time")
        else:
            return None
    @property
    def latitude(self):
        if self.node.get("position") and self.node.get("position").get("latitude"):
            return self.node.get("position").get("latitude")
        else:
            return None
    @property
    def longitude(self):
        if self.node.get("position") and self.node.get("position").get("longitude"):
            return self.node.get("position").get("longitude")
        else:
            return None
    # radio_num
    # user_id
    # longName
    # shortName
    # macaddr
    # hwModel
    # role
    # snr
    # lastHeard
    # batteryLevel
    # voltage
    # channelUtilization
    # airUtilTx
    # latitudeI
    # longitudeI
    # altitude
    # time
    # latitude
    # longitude

class MeshtasticUtils(object):

    def __init__(self, radio_path: Path, db_session: Session, node_table) -> SerialInterface:
        self.radio_path = radio_path
        self.Node = node_table
        self.session = db_session

        if not radio_path.exists():
            self.radio_disconnect_polling()
        self.interface = self.startup

    @property
    def startup(self):
        # Start setting up Meshtastic because Textual is ready
        # pub.subscribe(self.recv_text, "meshtastic.receive.text")
        # pub.subscribe(self.on_local_connection, "meshtastic.connection.established")
        # pub.subscribe(self.update_nodes, "meshtastic.node.updated")
        # pub.subscribe(self.disconnect_radio, "meshtastic.connection.lost")
        interface = meshtastic.serial_interface.SerialInterface(devPath=str(self.radio_path))
        return interface

    def on_local_connection(self, interface):
        """
            Called when a new radio connection is made
            """
        # Local radio information
        self.getMyUser = self.interface.getMyUser()
        self.radio_id = self.getMyUser.get("id")
        self.longName = self.getMyUser.get("longName")
        self.shortName = self.getMyUser.get("shortName")
        self.hwModel = self.getMyUser.get("hwModel")
        self.macaddr = self.getMyUser.get("macaddr")

        # Check if the node has been seen before
        resp = self.session.execute(select(self.Node).filter_by(macaddr=self.getMyUser.get("macaddr")))

        if len(resp.fetchall()) != 0:
            return resp.fetchall()
        else:
            return resp.fetchall()

    def recv_text(self, packet, interface):
        # print(f"{success_green} Incoming Message: {packet}")
        # print(f"{success_green} self.interface Information: {self.interface}")
        decoded_text = packet.get("decoded").get('text')
        # Date time msg received
        now = datetime.datetime.now()
        now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
        # Ljust is to make the formatting look better
        msg_string = f"{now_fmt.ljust(20, ' ')} [white bold]|[/] {decoded_text}"
        return msg_string

    def disconnect_radio(self, interface):
        """
        Called when a radio disconnect event is received.
        Quit and print to console
        """
        # Remove local radio from SQL

        if not self.radio_path.exists():
            self.radio_disconnect_polling()
        self.interface = self.startup

    def update_nodes(self, node, interface):
        return(f"Update Nodes {node}")

    def radio_disconnect_polling(self):
        start_time = datetime.datetime.now()
        while True:
            sleep(1)
            # console.print(f"{datetime.datetime.now() - start_time}")
            time_delta = datetime.datetime.now() - start_time
            if time_delta.seconds < 30:
                # If the radio path exists, try to connect to the radio
                if self.radio_path.exists():
                    # Do first startup sequence here
                    return self.radio_path
            else:
                sys.exit(1)