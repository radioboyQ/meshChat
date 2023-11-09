# goal to display messages received and send messages

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
# from pprint import pprint
import time


def on_receive(packet, interface, ):
    # print(packet)
    print("-" * 80)
    print({packet.get("decoded").get("portnum")})  # there are ADMIN_APP and TELEMETRY_APP messages
    whoToWho(packet)
    if packet.get("decoded").get("portnum") == "TEXT_MESSAGE_APP":
        text_message_app(packet)

    elif packet.get('decoded').get('portnum') == 'ADMIN_APP':
        adminApp(packet)

    elif packet.get('decoded').get('portnum') == 'TELEMETRY_APP':
        telemetryApp(packet)

    else:
        print("Warning New app" * 30)
        print(packet)
        pass


def whoToWho(packet):  # displays from and to information
    # calls some kind of form and to information - ^All is a global call to all radios
    print(f"whoToWho Function fromId was {str(packet.get('fromId'))} toId was {str(packet.get('toId'))}")
    return


def text_message_app(packet):  # displays messages sent over the mesh
    print("Message" * 10)
    print(
        f"Message from {str(packet.get('from'))}, To {str(packet.get('to'))} {str(packet.get('decoded').get('text'))}"
    )  # displays From ### : TEXT
    print(f"Message ID: {str(packet.get('id'))}")
    print("Message" * 10)
    return


def adminApp(packet):  # manages the ADMIN_APP packet
    from_packet = str(packet.get('fromId'))
    to_packet = str(packet.get('toId'))
    if from_packet == to_packet:
        print(f"{from_packet} is me!")
    else:
        pass
    print(
        f"adminApp function: From {str(packet.get('from'))}, To {str(packet.get('to'))} ")
    print("admin notes were:")
    print(f"{str(packet.get('decoded').get('admin'))}")
    return


def telemetryApp(packet):  # manages the TELEMETRY_APP packet
    print("telemetryApp function:")
    print(f"TELEMETRY_APP telemetry notes were: {str(packet.get('decoded').get('telemetry'))}")
    return


def main():
    # Subscribe to the given message type This should display received text
    # the below doesn't display telemetry data
    pub.subscribe(on_receive, "meshtastic.receive")
    # By default, will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
    interface = meshtastic.serial_interface.SerialInterface()

    # Main application "logic" - This holds the program open to maintain a connection with the radio. This function
    # will continue to print "..." to the screen unless it receives a message, both status and messages
    while True:
        # print("...")
        time.sleep(3)


main()
