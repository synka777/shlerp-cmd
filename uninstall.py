import json
import os
from os import environ
from os.path import join, exists
from utils import out
import click
import sys
import subprocess


def uninstall():
    with open(f'{os.getcwd()}/settings.json', 'r') as read_settings:
        settings = json.load(read_settings)
    home = os.path.expanduser("~")
    abs_setup_path = f'{home}/{settings["rel_setup_path"]}'
    setup_folder = f'{abs_setup_path}/shlerp/'

    shell = environ['SHELL']
    shell_string = shell.split('/')[2] if 'bash' in shell or 'zsh' in shell else None
    rc_file = f'.{shell_string}rc'
    rc_file_path = f'{home}/{rc_file}'

    # Step 1: Uninstall the function alias from the rc_file
    if exists(rc_file_path):
        with open(rc_file_path, 'r') as read_rc:
            double_check = True
            read_rc = read_rc.read()
            tmp_rc_path = f'{setup_folder}.rc_file'
            source_line = f'source {setup_folder}function.template'
            if source_line in read_rc:
                cleaned_rc = read_rc.replace(source_line, '')
                with open(tmp_rc_path, 'w') as write_tmp_rc:
                    write_tmp_rc.write(cleaned_rc)
                if exists(tmp_rc_path):
                    subprocess.run(["mv", tmp_rc_path, rc_file_path])
            else:
                double_check = False
                out(None, 'uninstall', 'I', f'[1/2] OK: Function not found in {rc_file}')

        if double_check:
            with open(rc_file_path, 'r') as read_rc:
                if source_line not in read_rc:
                    out(None, 'uninstall', 'I', f'[1/2] OK: Uninstalled the function from {rc_file}')
                else:
                    out(None, 'uninstall', 'E', f'[1/2] ERROR: Function still sourced in {rc_file}')

    # Step 2: Remove the installation folder
    subprocess.Popen([
        'rm', '-rf', f'{setup_folder}',
        '&&' f'{out(None, "uninstall", "I", f"[2/2] OK: Uninstalled shlerp from {setup_folder}")}'
    ])
    sys.exit(0)


if __name__ == '__main__':
    uninstall()
