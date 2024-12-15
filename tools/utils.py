from datetime import datetime
from os.path import exists
import subprocess
import re
import shutil
import os
import json

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


def req_installed(setup_folder):
    """Attempts to install requirements
    :param setup_folder: str representing the setup folder
    :return: True if it worked, else False
    """
    #try:
    venv_bin = f'{setup_folder}/venv/bin/'
    pip_path = f'{venv_bin}pip'
    try:
        # Use Popen with stdout and stderr as PIPE for real-time output
        process = subprocess.Popen(
            [pip_path, 'install', '-r', f'{setup_fld}/requirements.txt'],
            stdout=subprocess.PIPE,  # Capture stdout
            stderr=subprocess.PIPE,  # Capture stderr
            text=True                # Decode output as text (not bytes)
        )

        # Read output line by line in real-time
        # for line in process.stdout:
        #     print(line, end="")  # Print each line as it arrives

        # Wait for process to complete
        process.wait()

        # Check return code
        if process.returncode == 0:
            return True
        else:
            # print("Error during installation.")
            # print("stderr:", process.stderr.read())
            return False

    except Exception as e:
        print(f"An error occurred: {e}")
        return False
