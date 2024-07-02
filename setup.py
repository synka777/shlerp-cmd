import json
import os
from os import environ
from os.path import join, exists
import click
import utils
import platform
import shutil
import venv


def setup():
    project_files = (
        'main.py',
        'rules.json',
        'settings.json',
        'utils.py',
        'function.template'
    )
    with open(f'{os.getcwd()}/settings.json', 'r') as read_settings:
        settings = json.load(read_settings)
    home = os.path.expanduser("~")
    abs_setup_path = f'{home}/{settings["rel_setup_path"]}'
    setup_folder = f'{abs_setup_path}/shlerp/'
    current_os = platform.uname().system

    # Determine on which OS the script is running
    if current_os in ('Darwin', 'Linux'):
        count = 0
        for elem in project_files:
            if exists(f'{setup_folder}{elem}'):
                count += 1

        # Check if the project files are all installed. If so, notify the user
        if count == len(project_files):
            utils.out(None, 'setup', 'I', '[1/3] OK: Project files already installed')
        else:
            try:
                if not exists(setup_folder):
                    os.makedirs(setup_folder)
                for elem in project_files:
                    shutil.copy(f'./{elem}', f'{setup_folder}{elem}')
                    os.chmod(f'{setup_folder}{elem}', 0o500)
                    utils.out(None, 'setup', 'I', f'[1/3] OK: {setup_folder}{elem}')
                utils.out(None, 'setup', 'I', f'[1/3] OK: Copied the project into {setup_folder}')
            except FileNotFoundError as not_found_err:
                utils.out(None, 'setup', 'E', f'[1/3]{not_found_err}')

        # Add the alias into .bashrc/.zshrc
        shell = environ['SHELL']
        shell_string = shell.split('/')[2] if 'bash' in shell or 'zsh' in shell else None
        if not shell_string:
            utils.out(None, 'setup', 'E', '[2/3] Please use a bash or zsh shell to install the command system-wide')
        else:
            rc_file = f'.{shell_string}rc'
            read_rc = None
            if exists(f'{home}/{rc_file}'):
                with open(f'{home}/{rc_file}', 'r') as read_rc:
                    read_rc = read_rc.read()

            with open(f'{home}/{rc_file}', 'a') as write_rc:
                write = True
                if read_rc:
                    if 'shlerp' in read_rc:
                        write = False
                        utils.out(None, 'setup', 'I', '[2/3] OK: Alias function already installed')
                if write:
                    write_rc.write(f'source {setup_folder}function.template')
                    utils.out(None, 'setup', 'I', f'[2/3] OK: Alias added to {rc_file}')

        # Create a venv in the setup folder, installs the requirements by itself
        venv_folder = join(setup_folder, "venv")
        if not exists(venv_folder):
            venv.create(venv_folder, with_pip=True)
            utils.out(None, 'setup', 'I', '[3/3] OK: Virtual environment set up')
        else:
            utils.out(None, 'setup', 'I', '[3/3] OK: Virtual environment already installed')

    else:
        utils.out(None, 'setup', 'E', 'ERROR: This system is not supported')
        exit()


if __name__ == '__main__':
    setup()
