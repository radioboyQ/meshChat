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
    pub.subscribe(onConnection, "meshtastic.connection.established") # what the heck does this do?
    # By default, will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
    interface = meshtastic.serial_interface.SerialInterface() # sets a callable object called "interface" I think?

    # Main application "logic"
    message_number = 0  # starts the message number at 0
    run_time = 0 # starts run time at 0
    while True:
        interface.sendText(f"Test Message every 15 seconds - Message # {str(message_number)} Runtime {str(run_time)}")
        print(f"Sent Test Message - Message # {str(message_number)} Runtime {str(run_time)}")
        time.sleep(15)
        message_number = message_number + 1
        run_time = run_time + 15


main()
