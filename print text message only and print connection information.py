# this is a cleaned copy of meshchat_msg_test script. I commented out the message sending which occurs immediately on
# starting the script

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from pprint import pprint
import time

def onReceive(packet, interface,):
    # print(packet)
    print("-"*80)
    print({packet.get("decoded").get("portnum")})
    if packet.get("decoded").get("portnum") == "TEXT_MESSAGE_APP":
        print("*"*80)
        print(f"from {str(packet.get('from'))}")
        print(packet.get("decoded").get("text")) # this gets just the text message from the device
        print("*"*80)
        print(packet)
    else:
        print(packet)
        pass
    # there are ADMIN_APP and TELEMETRY_APP messages
    # else:
    #     print(packet)
def main():
    # Subscribe to the given message type This should display received text
    # the below doens't display telemetry data
    pub.subscribe(onReceive, "meshtastic.receive")
    # By default will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
    interface = meshtastic.serial_interface.SerialInterface()

    # Main application "logic" - This holds the program open to maintain a connection with the radio. This function
    # will continue to print "..." to the screen unless it receives a message, both status and messages
    while True:
        # print("...")
        time.sleep(3)

main()
