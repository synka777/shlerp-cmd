from datetime import datetime
from os.path import exists
from uuid import uuid4
import random
import subprocess
import mimetypes
import re
import shutil
import os
import json
import glob
import json
import sys
import time

# Cached data

settings = {}
app_details = {}

# Getter functions

def get_setup_fld():
    # Resolve the absolute path to the current script
    script_path = os.path.abspath(__file__)
    # Get the directory containing this script
    script_dir = os.path.dirname(script_path)
    # Get the parent directory of the script
    parent_dir = os.path.dirname(script_dir)
    return parent_dir


def get_app_details():
    global app_details
    if len(app_details) == 0:
        with open(f'{get_setup_fld()}/config/app_details.json', 'r') as read_details:
            for key, val in json.load(read_details).items():
                app_details[key] = val
    return app_details


def get_settings():
    global settings
    if len(settings) == 0:
        with open(f'{get_setup_fld()}/config/settings.json', 'r') as read_settings:
            for key, val in json.load(read_settings).items():
                settings[key] = val
    return settings


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

# Utilities that do not require pip installations

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


def get_file_size(archive_path):
    try:
        # Get the file size in bytes
        file_size = os.path.getsize(archive_path)
        # Convert the file size to megabytes
        file_size_mb = file_size / (1024 * 1024)
        return file_size_mb
    except OSError as e:
        # Handle the error if the file does not exist or is inaccessible
        return {"error": str(e)}


def spinner_animation(stop_event, message):
    """Function to animate the spinner in a separate thread."""
    spinner = ['\\', '|', '/', '-']
    spin_index = 0

    while not stop_event.is_set():  # Keep spinning until the event is set
        sys.stdout.write(f'\r{spinner[spin_index]} {message}')
        sys.stdout.flush()
        spin_index = (spin_index + 1) % len(spinner)
        time.sleep(0.1)
    sys.stdout.write('\r')  # Clear the spinner line when done


def remove_previous_line():
    """ Removes the previous line from the terminal output and move the cursor"""
    # Move the cursor up by one line
    sys.stdout.write("\033[F")  # ANSI escape code: Move cursor up one line
    # Clear the current line
    sys.stdout.write("\033[K")  # ANSI escape code: Clear from cursor to the end of the line
    # Ensure output is flushed
    sys.stdout.flush()


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
    get_settings()
    log_fld = f'{os.path.expanduser("~")}/{settings["rel_logs_path"]}'
    max_size = settings['logging']['no_prune']['max_log_size']
    max_age = settings['logging']['prune']['max_days']
    prune = settings['logging']['prune']['enabled']

    filename = f'{log_type}.log'
    log_file = None

    os.makedirs(log_fld, mode=0o775, exist_ok=True)

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
            # If only one log file, open the file in rw mode and prune the entries that are too old.
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


def iglob_hidden(*args, **kwargs):
    """A glob.iglob that include dot files and hidden files"""
    """The credits goes to the user polyvertex for this function"""
    old_ishidden = glob._ishidden
    glob._ishidden = lambda x: False
    try:
        yield from glob.iglob(*args, **kwargs)
    finally:
        glob._ishidden = old_ishidden


def is_archive(file_path):
    """Check if a given path corresponds to an archive file.
    :param file_path: Path to the file.
    :return: True if the file is an archive, False otherwise.
    """
    # Ensure the file exists
    if not os.path.isfile(file_path):
        return False

    # Check the MIME type of the file
    mime_type, _ = mimetypes.guess_type(file_path)

    # Common MIME types for archives
    archive_mime_types = [
        "application/zip",
        "application/x-tar",
        "application/x-gzip",
        "application/x-bzip2",
        "application/x-7z-compressed",
        "application/x-rar-compressed",
        "application/x-xz",
    ]

    # Return True if the MIME type matches known archive types
    return mime_type in archive_mime_types


def get_files(path, rules, options):
    """Lists the files contained in a given folder
    :param path: String referring to the path that needs its content to be listed
    :param rules: List of rules containing exclusions
    :param options: dictionary/object containing exclusion options
    :return: A list of files, without any possible node_modules folder
    """
    exclusions = {
        "files": set(),
        "folders": set(),
        "dep_folders": set()
    }

    # Handle nogit option
    if options['nogit']:
        rules.append(
            {
                "actions": {
                    "exclude": {
                        "files": ['.git'],
                        "folders": ['.gitignore']
                    }
                }
            }
        )

    # Collect exclusions from all rules
    for rule in rules:
        if 'actions' in rule and 'exclude' in rule['actions']:
            exclude = rule['actions']['exclude']
            if 'files' in exclude:
                exclusions['files'].update(exclude['files'])
            if 'folders' in exclude:
                exclusions['folders'].update(exclude['folders'])
            if 'dep_folders' in exclude:
                exclusions['dep_folders'].update(exclude['dep_folders'])

    # If the noexcl option is set to True, we return all the files in the folder except the dependency folder
    if options['noexcl']:
        return [
            file for file in os.listdir(path)
            if (exclusions['dep_folders'] and file not in exclusions['dep_folders'])
            or not exclusions['dep_folders']
        ]

    elem_list = []
    for elem in os.listdir(path):
        excl_matched = False
        elem_path = os.path.join(path, elem)

        if any(dep_folder in elem_path for dep_folder in exclusions['dep_folders']):
            excl_matched = True
        if any(excl in elem_path for excl in exclusions['folders']):
            excl_matched = True
        if any(excl in elem_path for excl in exclusions['files']):
            excl_matched = True

        if not excl_matched:
            if (
                not options['keephidden'] and
                elem.startswith('.') and
                not (
                    elem == '.git' or
                    elem == '.gitignore'
                )
            ):
                excl_matched = True

        if not excl_matched:
            elem_list.append(elem)

    return elem_list


def get_dependency_folders(rules):
    dep_folders = set()
    for rule in rules:
        _dep_folders = rule['actions']['exclude']['dep_folders']
        if _dep_folders:
            for folder in _dep_folders:
                dep_folders.add(folder)
    return dep_folders


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
    return [] if len(winner) == 0 else winner