"""
This is so there is a fixed point for us to shore up cross platform paths
Rather than needing to check in every single place that we use them
"""

import os
import sys
import tempfile


def ffmpeg_cmd():
    # todo why do we have the fullpath here?
    #  I recall that this is the location that brew installs to...
    #  but I can't remember why we wanted to avoid ambiguity here? multiple installs?
    cmd = '/usr/local/bin/ffmpeg'
    if sys.platform.startswith('win32'):
        cmd = "ffmpeg.exe"
    return cmd


def temp_directory(child_folder=''):
    path = "/tmp/mediasleuth"
    if sys.platform.startswith('win32'):
        path = os.path.join(tempfile.gettempdir(), "mediasleuth")

    # shortcut to this extending our path
    path = os.path.join(path, child_folder)

    return path


def config_directory(child_folder=''):
    path = "~/.mediasleuth/"
    if sys.platform.startswith('win32'):
        path = os.path.join(os.environ['APPDATA'], "mediasleuth")

    # shortcut to this extending our path
    path = os.path.join(path, child_folder)

    return path
