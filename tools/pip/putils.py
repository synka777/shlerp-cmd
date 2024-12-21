from datetime import datetime
from tools.utils import log, get_dt, get_settings, get_setup_fld
from uuid import uuid4
from os.path import exists
from click import echo
import requests
import pytz
import os
import random
import click
import glob
import json



# Common


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


def update_state(state, status, path):
    if status == 0:
        state['done'].append(path)
    elif status == 1:
        state['failed'].append(path)
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

        with open(f'{get_setup_fld()}/tmp/rules_history.json', 'w') as write_tmp:
            write_tmp.write(json.dumps(history_file, indent=4))
            return True
    except (FileNotFoundError, ValueError):
        with open(f'{get_setup_fld()}/tmp/rules_history.json', 'a') as write_tmp:
            write_tmp.write(json.dumps({
                "rules_history": [current_lang]
            }))
            if exists(f'{get_setup_fld()}/tmp/rules_history.json'):
                return True
    return False


def upload_archive(archive_path, expire_time):
    url = "https://file.io"

    with open(archive_path, "rb") as file:
        files = {'file': file}
        data = {'expires': expire_time}

        return requests.post(url, files=files, data=data)


def time_until_expiry(expiry_date_str):
    # Parse the expiration date string with UTC timezone
    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
    
    # Get the current date and time with UTC timezone
    current_date = datetime.now(pytz.UTC)
    
    # Calculate the difference
    difference = expiry_date - current_date
    
    # Get the total seconds from the difference
    total_seconds = difference.total_seconds()
    
    if total_seconds < 0:
        return "Expired"
    
    # Calculate days, hours, and minutes
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    if days > 1:
        return f"Expires in {days:.0f} days"
    elif days == 1:
        return f"Expires in 1 day"
    elif hours > 1:
        if minutes > 0:
            return f"Expires in {hours:.0f} hours and {minutes:.0f} minutes"
        else:
            return f"Expires in {hours:.0f} hours"
    elif hours == 1:
        if minutes > 0:
            return f"Expires in 1 hour and {minutes:.0f} minutes"
        else:
            return f"Expires in 1 hour"
    else:
        return f"Expires in {minutes:.0f} minutes"