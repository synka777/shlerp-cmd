import os
import json


def get_settings():
    with open(f'{os.getcwd()}/config/settings.json', 'r') as read_settings:
        return json.load(read_settings)


def get_app_details():
    with open(f'{os.getcwd()}/config/app_details.json', 'r') as read_app_details:
        return json.load(read_app_details)
