from datetime import datetime
from tools import utils
import threading
from tools.utils import log, get_dt, get_settings, get_setup_fld
from click import echo
import requests
import pytz
import click


# This file is there to list functions that are not be used in the setup script


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
            count = f'[{kwargs['cnt']}]'
        if 'input' in kwarg:
            u_input = True
    string = f'[{(f'{uid}:' if uid else '')}{get_dt()}:{step}]{count}[{lvl}] {message}'
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


def upload_archive(archive_path, expire_time):
    """Upload a file to file.io with a spinner animation.
    param: archive_path (str): The path to the file to be uploaded.
    param: expire_time (str): Expiration time in ISO 8601 or duration format (e.g., '14d').
    returns: Response: The response from the file.io API.
    """
    url = 'https://file.io'
    stop_event = threading.Event()  # Event to signal the spinner to stop

    # Start the spinner in a separate thread
    spinner_thread = threading.Thread(target=utils.spinner_animation, args=(stop_event, 'Uploading...'))
    spinner_thread.start()

    try:
        # Perform the upload
        with open(archive_path, 'rb') as file:
            files = {'file': file}
            data = {'expires': expire_time}
            response = requests.post(url, files=files, data=data)
    finally:
        # Stop the spinner once the request completes
        stop_event.set()
        spinner_thread.join()  # Wait for the spinner thread to exit

    return response


def time_until_expiry(expiry_date_str):
    # Parse the expiration date string with UTC timezone
    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)
    
    # Get the current date and time with UTC timezone
    current_date = datetime.now(pytz.UTC)
    
    # Calculate the difference
    difference = expiry_date - current_date
    
    # Get the total seconds from the difference
    total_seconds = difference.total_seconds()
    
    if total_seconds < 0:
        return 'Expired'
    
    # Calculate days, hours, and minutes
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    if days > 1:
        return f'Expires in {days:.0f} days'
    elif days == 1:
        return f'Expires in 1 day'
    elif hours > 1:
        if minutes > 0:
            return f'Expires in {hours:.0f} hours and {minutes:.0f} minutes'
        else:
            return f'Expires in {hours:.0f} hours'
    elif hours == 1:
        if minutes > 0:
            return f'Expires in 1 hour and {minutes:.0f} minutes'
        else:
            return f'Expires in 1 hour'
    else:
        return f'Expires in {minutes:.0f} minutes'