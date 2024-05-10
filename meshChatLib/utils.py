# Standard library imports
from collections import namedtuple
import datetime
import pickle
from pathlib import Path
from pprint import pprint
import sys
from time import strftime, localtime, sleep

import arrow
import meshtastic
from meshtastic.serial_interface import SerialInterface
from pubsub import pub


class MeshChatUtils(object):

    def __init__(self, pickle_path: Path):
        """
        dms = Direct MessageS

        namedTuple(
        msg_log_dict = {"dms":
                            sender_(radio_)id: [
                                                namedTuple("msg", "send_id receiver_id text_msg")
                                                ],
                        "channels":
                            channel_id: [
                                        namedTuple("channel", "sender_id text_msg channel", defaults=None
                                        ]
                        }
        """

        # Pickle to load the past messages from a file
        if pickle_path.exists():
            with open(pickle_path, 'rb') as f:
                self.msg_log_dict = pickle.load(f)
        else:
            # If pickle doesn't exist
            self.msg_log_dict = {"dms": {}, "channels": {}}

        # Generate the standard dms namedtuple
        self.msg_tuple = namedtuple("directMessage", ["sender", "receiver", "text_msg", "rx_dt"])

    def convert_short_datetime(self, datetime_obj: datetime.datetime):
        """
        Take in a date time object and convert it to "Minutes ago", "Hours ago", etc
        """
        now_fmt = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

        a_time = arrow.get(now_fmt)
        return a_time

    @property
    def status_time_prefix(self):
        # Date time msg received
        now = datetime.datetime.now()
        now_fmt = now.strftime('%Y-%m-%d %H:%M:%S')
        # Ljust is to make the formatting look better
        msg_string = f"{now_fmt.ljust(20, ' ')}"
        return msg_string

    def text_msg_for_printing(self, receiver: str, text_msg: str, rx_dt: datetime = datetime.datetime.now(), sender_name: str = None):
        time_formatted = rx_dt.strftime('%Y-%m-%d %H:%M:%S')
        # self.msg_log_dict["dms"]["radio_id"].append(self.msg_tuple(sender=radio_id, receiver=self.))
        # Return the full string
        return f"{time_formatted}[white bold]|[/][red bold] {sender_name} [/][white bold]>[/] {text_msg}"

    def record_dm_msg(self, sender_id: str, receiver_id: str, msg: str) -> None:
        now = datetime.datetime.now()
        if "dms" not in self.msg_log_dict:
            self.msg_log_dict.update({"dms": {sender_id: [self.msg_tuple(sender=sender_id, receiver=receiver_id, text_msg=msg,
                                                       rx_dt=now)]}})
        elif sender_id not in self.msg_log_dict["dms"]:
            # Create the dm if this is the first msg
            dms_dict_by_radio_id = self.msg_log_dict["dms"]
            dms_dict_by_radio_id.update({sender_id: [self.msg_tuple(sender=sender_id, receiver=receiver_id,
                                                                    text_msg=msg, rx_dt=now)]})
            self.msg_log_dict["dms"] = dms_dict_by_radio_id
        else:
            msg_list = self.msg_log_dict["dms"][sender_id]
            msg_list.append(self.msg_tuple(sender=sender_id, receiver=receiver_id, text_msg=msg, rx_dt=now))


    def record_channel_msg(self, channel_id: str, sender_id: str, receiver_id: str, msg: str):
        now = datetime.datetime.now()
        if channel_id not in self.msg_log_dict:
            # Create channel if this is a new channel
            channel_dict = self.msg_log_dict["channels"]
            channel_dict.update({sender_id: [self.msg_tuple(sender=sender_id, receiver=receiver_id, text_msg=msg,
                                                            rx_dt=now)]})
            self.msg_log_dict["channels"] = channel_dict
        else:
            msg_list = self.msg_log_dict["channels"][channel_id]
            msg_list.append(self.msg_tuple(sender=sender_id, receiver=receiver_id, text_msg=msg, rx_dt=now))
            self.msg_log_dict["channels"][channel_id] = msg_list

    def get_dms(self, radio_id) -> list:
        """
        Return the chat log of the specified radio
        """
        if "dms" in self.msg_log_dict and radio_id in self.msg_log_dict["dms"]:

            return self.msg_log_dict["dms"][radio_id]
        elif radio_id not in self.msg_log_dict["dms"]:
            return "No messages, yet."
        # return self.msg_log_dict["dms"][radio_id]

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
        super().__init__(raw_msg)
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