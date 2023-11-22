# Standard library imports
from time import strftime, localtime
from pprint import pprint

# Installed 3rd party modules
import click
from pubsub import pub
from rich.console import Console

# Import custom status symbols
from meshChatLib import (info_blue_splat,
                       info_green_splat,
                       warning_fmt,
                       prompt_yellow_question,
                       error_fmt,
                       success_green,
                       warning_triangle_yellow)
from meshChatLib.setup import Setup, Parser

@click.command("meshChat")
@click.option("-r", "--radio", help="Local path to the radio", default="/dev/ttyACM0", show_default=True,
              type=click.Path(exists=True, readable=True, writable=True, resolve_path=True, allow_dash=True))
@click.pass_context
def main(ctx, radio):
    console = Console()

    # Connect to the radio
    setup = Setup(console=console, radio_path=radio)
    # Instantiate Parser class
    parser = Parser(console=console)

    # Example code for publisher subscribe methods.
    pub.subscribe(parser.recv_text, "meshtastic.receive.text")
    pub.subscribe(parser.connection_lost, "meshtastic.connection.lost")
    # pub.subscribe(parser.onConnection, "meshtastic.connection.established")


    # console.print(f"{info_green_splat} Hopefully listening to {radio}")
    # with console.status("Waiting for incoming messages", spinner="dots") as spin:
    #     # Keep the spinner going while messages show up and are printed to screen
    #     while True:
    #         pass






if __name__ == "__main__":
    main()