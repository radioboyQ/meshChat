import meshtastic
import meshtastic.serial_interface
from pubsub import pub

import time

def onReceive(packet, interface): # called when a packet arrives
    print(f"Received: {packet}")

def onConnection(interface, topic=pub.AUTO_TOPIC): # called when we (re)connect to the radio
    # defaults to broadcast, specify a destination ID if you wish
    interface.sendText("hello mesh")

def main():
    # Subscribe to the given message type
    pub.subscribe(onReceive, "meshtastic.receive")
    pub.subscribe(onConnection, "meshtastic.connection.established")
    # By default will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
    interface = meshtastic.serial_interface.SerialInterface()

    # Main application "logic"
    while True:
        print("...")
        time.sleep(3)

main()
