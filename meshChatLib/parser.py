from rich.console import Console
import meshtastic
import meshtastic.serial_interface

"""
This module is a set of classes which will parse incoming messages into something reasonable we can use.
This will be all the error trapping and support functions for getting data into the app and a consistent way.
Classes in this file can be called across the app, and we'll have nice concise outputs to work with.
"""
