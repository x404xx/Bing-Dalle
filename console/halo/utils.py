"""Utilities for Halo library.
"""
import codecs
from shutil import get_terminal_size

import six
from colorama import init
from termcolor import colored

init(autoreset=True)


def colored_frame(frame, color):
    """Color the frame with given color and returns.

    Parameters
    ----------
    frame : str
        Frame to be colored
    color : str
        Color to be applied

    Returns
    -------
    str
        Colored frame
    """
    return colored(frame, color, attrs=["bold"])


def is_text_type(text):
    """Check if given parameter is a string or not

    Parameters
    ----------
    text : *
        Parameter to be checked for text type

    Returns
    -------
    bool
        Whether parameter is a string or not
    """
    if isinstance(text, six.text_type) or isinstance(text, six.string_types):
        return True

    return False


def decode_utf_8_text(text):
    """Decode the text from utf-8 format

    Parameters
    ----------
    text : str
        String to be decoded

    Returns
    -------
    str
        Decoded string
    """
    try:
        return codecs.decode(text, "utf-8")
    except (TypeError, ValueError):
        return text


def encode_utf_8_text(text):
    """Encodes the text to utf-8 format

    Parameters
    ----------
    text : str
        String to be encoded

    Returns
    -------
    str
        Encoded string
    """
    try:
        return codecs.encode(text, "utf-8", "ignore")
    except (TypeError, ValueError):
        return text


def get_terminal_columns():
    """Determine the amount of available columns in the terminal

    Returns
    -------
    int
        Terminal width
    """
    terminal_size = get_terminal_size()

    if terminal_size.columns == 0:
        return 80
    else:
        return terminal_size.columns
