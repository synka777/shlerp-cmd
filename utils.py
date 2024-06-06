import os
import random
from uuid import uuid4
from datetime import datetime


def exists(path):
    """Checks if a file or folder exists
    :param path: String referring to the path we want to check
    :return: A boolean
    """
    return True if os.path.exists(path) else False


def get_files(path):
    """Lists the files contained in a given folder, without symlinks
    :param path: String referring to the path that needs it's content to be listed
    :return: A list of files, without any possible node_modules folder
    """
    return [file for file in os.listdir(path) if file != 'node_modules']


def get_dt():
    """
    :return: A timestamp in string format
    """
    return str(datetime.now().strftime('%d%m%y%H%M%S'))


def suid():
    """Generates a short uid
    :return: A unique identifier with a fixed length of 6 characters
    """
    chunks = str(uuid4()).split('-')
    count = 0
    uid = ''
    while count < 3:
        chunk = random.choice(chunks)
        uid = f'{uid}{chunk[:2]}'
        chunks.remove(chunk)
        count += 1
    return uid
