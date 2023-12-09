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

"""
This module is a set of classes which will parse incoming messages into something reasonable we can use.
This will be all the error trapping and support functions for getting data into the app and a consistent way.
Classes in this file can be called across the app, and we'll have nice concise outputs to work with.
"""


class Setup():
    """
    Conduct initial setup of the Meshtastic radio
    """

    def __init__(self, console: Console, radio_path: str = "/dev/ttyACM0"):
        """
        Connect to the radio and set it up for receiving messages
        :param radio_path: str
        """

        # Make console class obj
        self.console = console

        # Create SQL tables and connect to the database
        # Database tables
        # Boilerplate for creating a SQL database
        # sqlite:////tmp/test.sqlite = /tmp/test.sqlite
        self.engine = db.create_engine('sqlite:////tmp/test.sqlite')
        self.conn = self.engine.connect()
        metadata = MetaData()

        # Create the format for the table "local_radio"
        # This format tells the ORM what to expect and what the columns should be named
        # This is not data input, it's just formatting
        self.local_radio = Table(
            'local_radio', metadata,
            Column('id', Integer, primary_key=True),
            Column("local_node_id", String),
            Column("firmware_version", String),
            Column("device_state_version", Integer),
            Column("canShutdown", Boolean),
            Column("hasWifi", Boolean),
            Column("hasBluetooth", Boolean),
            Column("position_flags", Integer),
            Column("hw_model", String),
            Column("macaddr", String),
            Column("long_name", String),
            Column("short_name", String),
            Column("first_seen", DateTime),
            Column("last_seen", DateTime))

        # Create any tables that aren't already created
        metadata.create_all(self.engine)


        # supported_devices = detect_supported_devices()
        # for i in supported_devices:
        #     print(f" name:{i.name}{i.version} firmware:{i.for_firmware}")
        #
        # ports_list = active_ports_on_supported_devices(supported_devices)

        ports = findPorts(eliminate_duplicates=False)
        # No ports are listed, no supported devices found
        if len(ports) == 0:
            console.print(f"{error_fmt} No supported radios found. Try again.")
            sys.exit(1)

        # When a radio matches the one called for, set this bool to be true
        found = False

        # Iterate over supported radios on host
        for p in ports:
            # If the user requested radio is present, use it
            if radio_path == p:
                # Tell the user something
                console.print(f"{info_green_splat} Using radio on port {ports[0]}")
                # Set this to true
                found = True
                # Stop looping, no reason to continue after we find the radio
                break

        # If we didn't find the radio the user asked for
        if found is False:
            # And there's more than one possible radio, error
            if len(ports) > 1:
                console.print(f"{warning_triangle_yellow} There is {len(ports)} radios available. Try again.")
                sys.exit(1)



        # Record each radio

        # Grab the radio from the path provided and error checked earlier
        self.interface = meshtastic.serial_interface.SerialInterface(devPath=radio_path)

        # console.print(inspect(self.interface))
        # console.print(self.interface.metadata.hasWifi)
        # self.interface.showInfo()

        # Iterate over all the nodes on the self.interface
        # Grab each node and check if it's our local node. When it is, put all the data into the database
        if self.interface.nodes:
            for node in self.interface.nodes.values():
                local_node_num = self.interface.myInfo.my_node_num
                if node["num"] == self.interface.myInfo.my_node_num:
                    # console.print(inspect(self.interface))
                    local_node_id = node.get("user").get("id")
                    long_name = node.get("user").get("longName")
                    short_name = node.get("user").get("shortName")
                    macaddr = node.get("user").get("macaddr")
                    # Record the information from the local node
                    # Prep the ORM command to insert data from .values( into the database
                    new_radio = db.insert(self.local_radio).values(local_node_id=local_node_id,
                                                                   long_name=long_name,
                                                                   short_name=short_name,
                                                                   firmware_version=self.interface.metadata.firmware_version,
                                                                   device_state_version=self.interface.metadata.device_state_version,
                                                                   macaddr=macaddr,
                                                                   canShutdown=self.interface.metadata.canShutdown,
                                                                   hasWifi=self.interface.metadata.hasWifi,
                                                                   hasBluetooth=self.interface.metadata.hasBluetooth,
                                                                   position_flags=self.interface.metadata.position_flags,
                                                                   hw_model=self.interface.metadata.hw_model,
                                                                   first_seen=datetime.datetime.now(),
                                                                   last_seen=datetime.datetime.now())
                    # console.print(inspect(new_radio))

                    # Insert the data into the database
                    self.conn.execute(new_radio)

                    # Check the output and print everything in the table
                    # console.print(self.conn.execute(self.local_radio.select()).fetchall())


        else:
            console.print(f"{error_fmt} No nodes found")
        # console.print(inspect(self.interface))

        # End of instance creation


    def interface_close(self):
        self.interface.close()
