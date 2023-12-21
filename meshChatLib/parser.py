import datetime
import sys

import meshtastic
import meshtastic.serial_interface
import sqlalchemy as db
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey, Table, Column, Integer, String, MetaData, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from meshtastic.util import (
    active_ports_on_supported_devices,
    detect_supported_devices,
    get_unique_vendor_ids,
    findPorts,
)


from rich.console import Console
from rich import inspect

from . import (info_blue_splat,
               info_green_splat,
               warning_fmt,
               prompt_yellow_question,
               error_fmt,
               success_green,
               warning_triangle_yellow)

class Parser():
    """
    Parser functions when a new msg is received
    """

    def __init__(self, radio_path):
        self.radio_path = radio_path

    def recv_text(self, packet, interface):
        pass
    def onConnection(self, interface):
        pass

    def connection_lost(self, interface):
        self.console.print(f"{error_fmt} Connection to radio {self.interface} has been lost")