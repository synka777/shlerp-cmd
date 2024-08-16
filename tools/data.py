import os
import json


# Cached data

settings = {}
app_details = {}


# Getter functions

def get_settings():
    global settings
    if len(settings) == 0:
        with open(f'{os.getcwd()}/config/settings.json', 'r') as read_settings:
            for key, val in json.load(read_settings).items():
                settings[key] = val
    return settings


def get_app_details():
    global app_details
    if len(app_details) == 0:
        with open(f'{os.getcwd()}/config/app_details.json', 'r') as read_details:
            for key, val in json.load(read_details).items():
                app_details[key] = val
    return app_details
