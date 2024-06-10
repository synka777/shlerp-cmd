import os
import random
from uuid import uuid4
from datetime import datetime
from click import echo


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


def weight_found(contenders):
    """Self-explanatory
    :param contenders: List of objects representing potential winners
    :return: True if some patterns has a weight
    """
    for cont in contenders:
        if cont['weight'] > 0:
            return True
    return False


def elect(contenders):
    """Determines which language pattern(s) has the heavier weight
    :param contenders: List of objects representing potential winners
    :return: The object(s) that has the heaviest weight
    """
    winner = []
    contenders.sort(key=lambda x: x['weight'], reverse=True)
    for cont in contenders:
        if not winner:
            winner.append(cont)
        else:
            if cont['weight'] == winner[0]['weight']:
                winner.append(cont)
    return None if len(winner) == 0 else winner


def crawl_for_weight(contenders):
    # TODO: If nothing matched or no clear winner, crawl the project to find files matching the ext(s)
    echo('Crawling...')
    return []
