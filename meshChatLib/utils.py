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
        msg_string = f"{now_fmt.ljust(20, ' ')} [white bold]|[/]"
        return msg_string

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