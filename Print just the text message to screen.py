# this is a cleaned copy of meshchat_msg_test script. I commented out the message sending which occurs immediately on
# starting the script

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from pprint import pprint
import time

def onReceive(packet, interface,):
    # print(type(packet))
    # pprint(packet)
    print(packet.get("decoded").get("text")) # this gets just the text message from the device

def main():
    # Subscribe to the given message type This should display certain meshtastic messages like onReceive and
    # onConnection
    # the below doens't display telemetry data
    pub.subscribe(onReceive, "meshtastic.receive.text")
    # pub.subscribe(onReceive, "meshtastic.receive")
    # pub.subscribe(onConnection, "meshtastic.connection.established")
    # By default will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
    interface = meshtastic.serial_interface.SerialInterface()

    # Main application "logic" - This holds the program open to maintain a connection with the radio. This function
    # will continue to print "..." to the screen unless it receives a message, both status and messages
    while True:
        # print("...")
        time.sleep(3)

main()
