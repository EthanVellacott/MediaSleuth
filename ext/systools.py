"""
EKV 2019
- made portable
Single python file
Only builtin libraries

Basic command line function equivalents, so you don't need to reinvent the wheel all the time
TODO right now, most of these are just wrappers for *nix commands
 perhaps these can get rewritten in a python native way
"""

import os
import subprocess
import pathlib
import shutil


# PYTHON NATIVE

def cat(path):
    """
    Read a file

    TODO make the error handling better here
    """
    data = ''

    try:
        with open(path, 'r') as f:
            data = f.read()
    except Exception:
        print("WARNING: file could not be read {}".format(path))

    return data


def mkdir(new_dir):
    """
    Make a directory

    This ensures all parent directories are also created
    """
    pathlib.Path(new_dir).mkdir(parents=True, exist_ok=True)


def rm(to_remove):
    """
    Delete a file, or a folder and it's contents
    """
    if os.path.isdir(to_remove):
        shutil.rmtree(to_remove)
    else:
        os.remove(to_remove)


def cp(from_path, to_path):
    """
    Copy a file from_path to_path
    """
    shutil.copy2(from_path, to_path)


# COMMAND LINE WRAPPED

def rsync(from_path, to_path):
    """
    Rsync a file from_path into the directory of to_path

    In order to make this a little safer than in the command line, we make the directory on the other side first
    Personally, this is my preferred way, because it is more consistent

    This means that you can't use syntax where you would sync a single file using to_path as the full path
    I find it is more common for a single file to become what ought to have been a folder
    If this were a publicly available library I might need/want to walk that back
    """
    mkdir(to_path)
    cmd = 'rsync -a {0} {1} ; '.format(from_path, to_path)
    return run_cmd(cmd)


def copy_substitute(from_path, to_path, substitute_from, substitute_to):
    """
    Copy a file from_path into the directory of to_path, while substituting the filenames

    TODO reconsider this
    """
    mkdir(to_path)
    cmd = 'cp -r {0} $( echo {1} | sed "s/{2}/{3}/" ) ; '.format(from_path, to_path, substitute_from, substitute_to)
    return run_cmd(cmd)


def unzip(from_path, to_path):
    """
    Unzip a file to the directory of to_path
    """
    mkdir(to_path)
    cmd = 'unzip -qq {0} -d {1} ; '.format(from_path, to_path)
    return run_cmd(cmd)


def unrar(from_path, to_path):
    """
    Unrar a file to the directory of to_path
    """
    mkdir(to_path)
    cmd = 'unrar x {0} {1} > /dev/null ; '.format(from_path, to_path)
    return run_cmd(cmd)


def mail(subject, body, recipient, body_is_path=False):
    """
    Send an email
    """
    file_contents = 'echo {}'.format(body)
    if body_is_path:
        file_contents = 'cat {}'.format(body)

    cmd = '{} | mail -s {}  {}  ; '.format(file_contents, subject, recipient)
    return run_cmd(cmd)

# META UTILITY


def run_cmd(cmd):
    out = subprocess.call(cmd, shell=True)
    # print cmd
    return out
