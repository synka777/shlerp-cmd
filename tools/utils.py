from tools.data import get_settings
from uuid import uuid4
from datetime import datetime
from os.path import exists
from click import echo
import os
import random
import subprocess
import click
import glob
import json
import shutil
import re


# Common

def iterate_log_name(log_name):
    name_chunk = log_name.split('.')[0]
    ext_chunk = log_name.split('.')[1]
    split_attempt = name_chunk.split('-')
    base_name = split_attempt[0]

    if len(split_attempt) > 1:
        integer = int(split_attempt[1])
        integer += 1
    else:
        integer = 1
    return f'{base_name}-{integer}.{ext_chunk}'


def log(msg, log_type):
    settings = get_settings()
    log_fld = f'{os.path.expanduser("~")}/{settings["rel_logs_path"]}'
    max_size = settings['logging']['no_prune']['max_log_size']
    max_age = settings['logging']['prune']['max_days']
    prune = settings['logging']['prune']['enabled']

    filename = f'{log_type}.log'
    log_file = None

    if not exists(log_fld):
        os.makedirs(log_fld)

    log_files = [
        filename for filename in os.listdir(log_fld)
        if log_type in filename
    ]

    if prune:
        #####################
        # One log by log type

        if len(log_files) == 0:
            log_file = f'{log_type}.log'
            abs_log_file = f'{log_fld}/{log_file}'
            with open(abs_log_file, 'w+'):
                pass

        if len(log_files) > 1:
            # If more than one log file by log type, place the old logs into an archive sub-folder.
            # Can happen if the program has been switched back to the default auto_prune mode.
            old_logs_fld = f'{log_fld}/old_logs'
            if not exists(old_logs_fld):
                os.mkdir(old_logs_fld)

            # Then move all the logs to the old_logs folder
            for log_file in log_files:
                shutil.move(f'{log_fld}/{log_file}', f'{log_fld}/old_logs/{log_file}')

            log_file = f'{log_fld}{log_type}.log'

        elif len(log_files) == 1:
            log_file = log_files[0]
            # If only one log file, open the file in rw mode and prune the jobs that are too old.
            with open(f'{log_fld}/{log_files[0]}', 'r') as prune_file:
                now = datetime.now()
                valid_entries = []
                prune = False
                for index, line in enumerate(prune_file.readlines()):
                    str_date = re.match(r"\[(.*?:)?(.*?):[a-z]+\]", line).group(2)
                    year = str_date[0:4]
                    month = str_date[4:6]
                    day = str_date[6:8]
                    date = datetime.strptime(f'{year}{month}{day}', '%Y%m%d')

                    days = (now - date).days
                    if days < max_age:
                        if index == 1:  # If the first entry is valid, then we don't scan the rest of the file
                            break
                        # Else if the date is valid, add the line to the content that we'll write into the log
                        valid_entries.append(line)
                    else:
                        prune = True

                # Then, overwrite the log file with the entries that are recent enough to be kept in the logs.
                if prune:
                    with open(f'{log_fld}/{log_files[0]}', 'w') as update_file:
                        update_file.truncate(0)
                        for entry in valid_entries:
                            update_file.write(entry)
    else:
        #####################
        # Multiple logs

        # Determine which log file is the latest according to its date and type
        if len(log_files) > 1:
            c_dates = [(file, os.path.getctime(f'{log_fld}/{file}')) for file in log_files]
            log_file = sorted(c_dates, reverse=True, key=lambda x: x[1])[0][0]  # sort by creation time
        elif len(log_files) == 1:
            log_file = log_files[0]
        else:
            # If no log file found, use the filename template to create a new one afterwards
            log_file = filename

        # Then check the size of this log file
        if exists(f'{log_fld}/{log_file}'):
            log_size = os.path.getsize(f'{log_fld}/{log_file}')
            if log_size >= max_size:
                log_file = iterate_log_name(log_file)

    with open(f'{log_fld}/{log_file}', 'a+') as write_log:
        write_log.write(f'{msg}\n')


def s_print(step, lvl, message, *args, **kwargs):
    """Standardizes the output format
    :param step, short string that indicates to the user the step we are going through
    :param lvl, letter that indicates if the displayed message is an Info, Warning or Error
    :param message, the message we want to print
    :param *args, (optional) it's only expected to receive a string representing an uid.
    :return: The user input if input is set to True
    """
    uid = None
    u_input = False
    count = ''
    log_type = 'exec'
    if step == 'setup':
        log_type = step
    if step == 'uninstall':
        log_type = step
    if len(args) > 0:
        uid = args[0]
    for kwarg, val in kwargs.items():
        if 'cnt' in kwarg and val != '':
            count = f'[{kwargs["cnt"]}]'
        if 'input' in kwarg:
            u_input = True
    string = f"[{(f'{uid}:' if uid else '')}{get_dt()}:{step}]{count}[{lvl}] {message}"
    log(string, log_type)

    if lvl == 'I':
        if not u_input:
            echo(string)
        else:
            return input(string)
    else:
        color = None
        if lvl == 'E':
            color = 'red'
        if lvl == 'W':
            color = 'bright_yellow'
        if not u_input:
            echo(click.style(string, fg=color))
        else:
            return input(click.style(string, fg=color))


def get_dt():
    """
    :return: A datetime in string format
    """
    return str(
        datetime.now()
        .isoformat('#', 'seconds')
        .replace('-', '')
        .replace(':', '')
    )


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


# Shlerp script


def update_state(state, status):
    if status == 0:
        state['done'] += 1
    elif status == 1:
        state['failed'] += 1
    return state


def iglob_hidden(*args, **kwargs):
    """A glob.iglob that include dot files and hidden files"""
    """The credits goes to the user polyvertex for this function"""
    old_ishidden = glob._ishidden
    glob._ishidden = lambda x: False
    try:
        yield from glob.iglob(*args, **kwargs)
    finally:
        glob._ishidden = old_ishidden


def get_files(path, exclusions, options):
    """Lists the files contained in a given folder, without symlinks
    :param path: String referring to the path that needs it's content to be listed
    :param exclusions: Dictionary containing the files and folders we want to exclude
    :param options: dictionary/object containing exclusion options
    :return: A list of files, without any possible node_modules folder
    """
    if options['nogit']:
        exclusions['folders'].append('.git')
        exclusions['files'].append('.gitignore')
    if options['noexcl']:
        return [
            file for file in os.listdir(path)
            if (exclusions['dep_folder'] and file != exclusions['dep_folder'])
               or not exclusions['dep_folder']
        ]
    elem_list = []
    dep_fld = exclusions['dep_folder']
    for elem in os.listdir(path):
        excl_matched = False
        if (
                not options['keephidden'] and
                elem.startswith('.') and
                not (
                        elem == '.git' or
                        elem == '.gitignore'
                )
        ):
            excl_matched = True
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


def elect(leads):
    """Determines which language pattern(s) has the heavier weight
    :param leads: List of objects representing potential winners
    :return: The object(s) that has the heaviest weight
    """
    winner = []
    if leads:
        leads.sort(key=lambda x: x['total'], reverse=True)
        for lead in leads:
            if not winner:
                winner.append(lead)
            else:
                if lead['total'] == winner[0]['total']:
                    winner.append(lead)
    return None if len(winner) == 0 else winner


def crawl_for_weight(proj_fld, rules):
    """Crawl the project to find files matching the extensions we provide to this function
    :param proj_fld: text, the folder we want to process
    :param rules: object list containing languages names, extensions to crawl and weights
    :return: an updated list with some more weight (hopefully)
    """
    for rule in rules:
        if 'total' not in rule.keys():
            rule['total'] = 0
        for ext_elem in rule['detect']['extensions']:
            for ext in ext_elem['names']:
                for _ in glob.iglob(f'{proj_fld}/**/{ext}', recursive=True):
                    rule['total'] += ext_elem['weight']
    return rules


def enforce_limit(history_file, settings):
    """Shortens the history if it is too long compared to history_limit parameters.
    Can happen if these parameters have been reduced between two shlerp script executions
    :param history_file: Temporary file containing the history lists
    :param settings: shlerp settings
    """
    history_limits = settings['rules']['history_limit']
    rule_types = history_limits.keys()
    # Will cut the history if the length is superior to what is set up in the settings,
    # rule_types being 'frameworks' and 'vanilla'
    for rule_type in rule_types:
        if len(history_file[rule_type]) > history_limits[rule_type]:
            history_file[rule_type] = history_file[rule_type][:history_limits[rule_type]]
            with open('tmp/rules_history.json', 'w') as write_tmp:
                # Updates the history according to the rule type that has been elected
                write_tmp.write(json.dumps(history_file, indent=4))


def history_updated(rule, history_file, framework):
    """Updates the history with a new rule
    :param rule: List of dicts representing potential winners
    :param history_file: Temporary file containing the history list
    :param framework: Boolean that allows to tell the functon if the rule to add is vanilla or framework
    :return: A boolean depending on the outcome of this function
    """
    current_lang = rule['name']
    try:
        settings = get_settings()
        enforce_limit(history_file, settings)
        history_limits = settings['rules']['history_limit']
        rule_type = 'frameworks' if framework else 'vanilla'
        history = history_file[rule_type]
        history_limit = history_limits[rule_type]
        # If the current language is in the history
        if current_lang in history:
            # But it's not the latest, get its position and remove it to add it back in first pos
            if history.index(current_lang) != 0:
                current_pos = history.index(current_lang)
                history.pop(current_pos)
                history.insert(0, current_lang)
        else:
            # If the current language isn't in the list, remove the oldest one if needed and then add it
            if len(history) == history_limit:
                history.pop()
            history.insert(0, current_lang)

        with open(f'{os.getcwd()}/tmp/rules_history.json', 'w') as write_tmp:
            write_tmp.write(json.dumps(history_file, indent=4))
            return True
    except (FileNotFoundError, ValueError):
        with open(f'{os.getcwd()}/tmp/rules_history.json', 'a') as write_tmp:
            write_tmp.write(json.dumps({
                "rules_history": [current_lang]
            }))
            if exists(f'{os.getcwd()}/tmp/rules_history.json'):
                return True
    return False


# Setup script

def req_installed(setup_folder):
    """Attempts to install requirements
    :param setup_folder: str representing the setup folder
    :return: True if it worked, else False
    """
    try:
        venv_bin = f'{setup_folder}venv/bin/'
        pip_path = f'{venv_bin}pip'
        if not exists(pip_path):
            if exists(f'{venv_bin}pip3'):
                pip_path = f'{venv_bin}pip3'
            else:
                return False
        subprocess.check_call([
            pip_path,
            'install', '-r',
            f'{os.getcwd()}/requirements.txt'
        ])
        return True
    except subprocess.CalledProcessError:
        return False
