import os
import random
from uuid import uuid4
from datetime import datetime
from click import echo
import glob
import json


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


def crawl_for_weight(proj_fld, contenders):
    """Crawl the project to find files matching the extensions we provide to this function
    :param proj_fld: text, the folder we want to process
    :param contenders: object list containing languages names, extensions to crawl and weights
    :return: an updated list with some more weight (hopefully)
    """
    echo('Crawling...')
    for cont in contenders:
        for ext in cont['extensions']:
            for _ in glob.iglob(f'{proj_fld}/**/{ext["name"]}', recursive=True):
                cont['weight'] += ext['weight']
    return contenders


def enforce_limit(tmp_file, settings):
    """Shortens the history if it is too long compared to history_limit
    :param tmp_file: Temporary file containing the history list
    :param settings: Param representing
    :return:
    """
    history = tmp_file['rules_history']
    history_limit = settings['rules']['history_limit']
    if len(history) > history_limit:
        history = history[:history_limit]
        with open('tmp.json', 'w') as write_tmp:
            tmp_file['rules_history'] = history
            write_tmp.write(json.dumps(tmp_file, indent=4))


def history_updated(rule, settings, tmp_file):
    """Updates the history with a new rule
    :param rule:  List of objects representing potential winners
    :param settings: The settings of the project
    :param tmp_file:
    :return: A boolean depending on the outcome of this function
    """
    current_lang = rule['name']
    try:
        enforce_limit(tmp_file, settings)
        history = tmp_file['rules_history']
        history_limit = settings['rules']['history_limit']
        # If the current language is in the history
        if current_lang in history:
            # But it's not the latest, get its position and remove it to add it back in first pos
            if history.index(current_lang) != 0:
                current_pos = history.index(current_lang)
                history.pop(current_pos)
                history.insert(0, current_lang)
                with open('tmp.json', 'w') as write_tmp:
                    tmp_file['rules_history'] = history
                    write_tmp.write(json.dumps(tmp_file, indent=4))
                    return True
            return True
        else:
            # If the current language isn't in the list, remove the oldest one if needed and then add it
            if len(history) == history_limit:
                history.pop()
            history.insert(0, current_lang)
            tmp_file['rules_history'] = history
            with open('tmp.json', 'w') as write_tmp:
                write_tmp.write(json.dumps(tmp_file, indent=4))
                return True
    except (FileNotFoundError, ValueError):
        with open("./tmp.json", 'a') as write_tmp:
            write_tmp.write(json.dumps({
                "rules_history": [current_lang]
            }))
            if exists("./tmp.json"):
                return True
    return False
