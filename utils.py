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


def out(uid, operation, lvl, message):
    echo(f'[{uid}:{get_dt()}:{operation}][{lvl}] {message}')


def get_files(path, exclusions, noexcl, nogit):
    """Lists the files contained in a given folder, without symlinks
    :param path: String referring to the path that needs it's content to be listed
    :param exclusions: Dictionary containing the files and folders we want to exclude
    :param noexcl: boolean, disables the exclusions if True
    :param nogit: boolean, excludes git data from the backup
    :return: A list of files, without any possible node_modules folder
    """
    if nogit:
        exclusions['folders'].append('.git')
        exclusions['files'].append('.gitignore')
    if noexcl:
        return [
            file for file in os.listdir(path)
            if (exclusions['dep_folder'] and file != exclusions['dep_folder'])
            or not exclusions['dep_folder']
        ]
    elem_list = []
    dep_fld = exclusions['dep_folder']
    for elem in os.listdir(path):
        excl_matched = False
        if os.path.isdir(f'{path}/{elem}'):
            if exclusions['folders']:
                for fld_excl in exclusions['folders']:
                    if fld_excl in elem:
                        excl_matched = True
                        break
            if dep_fld and dep_fld in elem:
                excl_matched = True
            if not excl_matched:
                elem_list.append(elem)
        else:
            if exclusions['files']:
                for file_excl in exclusions['files']:
                    if file_excl in elem:
                        excl_matched = True
                        break
            if dep_fld and dep_fld in elem:
                excl_matched = True
            if not excl_matched:
                elem_list.append(elem)
    return elem_list


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


def weight_found(leads):
    """Self-explanatory
    :param leads: List of objects representing potential winners
    :return: True if some patterns has a weight
    """
    for lead in leads:
        if lead['total'] > 0:
            return True
    return False


def elect(leads):
    """Determines which language pattern(s) has the heavier weight
    :param leads: List of objects representing potential winners
    :return: The object(s) that has the heaviest weight
    """
    winner = []
    leads.sort(key=lambda x: x['total'], reverse=True)
    for lead in leads:
        if not winner:
            winner.append(lead)
        else:
            if lead['total'] == winner[0]['total']:
                winner.append(lead)
    return None if len(winner) == 0 else winner


def crawl_for_weight(proj_fld, leads, uid):
    """Crawl the project to find files matching the extensions we provide to this function
    :param uid: identifier representing the current program run
    :param proj_fld: text, the folder we want to process
    :param leads: object list containing languages names, extensions to crawl and weights
    :return: an updated list with some more weight (hopefully)
    """
    out(uid, 'scan', 'I', 'Crawling...')
    for lead in leads:
        for ext in lead['extensions']:
            for _ in glob.iglob(f'{proj_fld}/**/{ext["name"]}', recursive=True):
                lead['total'] += ext['weight']
    return leads


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
