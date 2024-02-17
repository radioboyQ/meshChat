# Standard library imports
import datetime
from pathlib import Path
from pprint import pprint
import sys
from time import strftime, localtime, sleep

import meshtastic
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

# Action succeeded
info_green_splat = f"[white][bold][[green]*[white]][/white][/bold][/green][/]"
# About to take an action
info_blue_splat = f"[white][bold][[blue]*[white]][/white][/bold][/blue][/]"
# Prompt
prompt_yellow_question = f"[white][bold][[yellow]?[white]][/white][/bold][/yellow][/]"
# Regular Warning
warning_fmt = f"[white][bold][[yellow]Δ[white]][/white][/bold][/yellow][/]"
# Extra Warning
warning_triangle_yellow = f"[white][bold][[yellow]>[white]][/white][/bold][/yellow][/]"
# Error
error_fmt = f"[white][bold][[red]![white]][/white][/bold][/red][/]"
#Winning
success_green = f"[white][bold][[green]+[white]][/white][/bold][/green][/]"
