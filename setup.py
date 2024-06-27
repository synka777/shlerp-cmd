import click
import utils
import os
import platform
import shutil
from os import environ
import subprocess
import sys


def setup():
    project_files = (
        'main.py',
        'rules.json',
        'settings.json',
        'utils.py'
    )
    home = os.path.expanduser("~")
    local_bin = f'{home}/.local/bin'
    setup_folder = f'{local_bin}/bumsaver/'
    current_os = platform.uname().system

    # Determine on which OS the script is running
    if current_os in ('Darwin', 'Linux'):
        count = 0
        for elem in project_files:
            if utils.exists(f'{setup_folder}{elem}'):
                count += 1

        # Check if the project files are all installed. If so, notify the user
        if count == len(project_files):
            utils.out(None, 'setup', 'I', 'Project files already installed')
        else:
            try:
                if not utils.exists(setup_folder):
                    os.makedirs(setup_folder)
                for elem in project_files:
                    shutil.copy(f'./{elem}', f'{setup_folder}{elem}')
                    print(f'{setup_folder}{elem}')
                    os.chmod(f'{setup_folder}{elem}', 0o500)
                utils.out(None, 'setup', 'I', f'Copied the project into {setup_folder}')
            except FileNotFoundError as not_found_err:
                utils.out(None, 'setup', 'E', not_found_err)

        # Add the alias into .bashrc/.zshrc
        with open('./function.template', 'r') as alias_function:
            alias_function = alias_function.read()
            shell = environ['SHELL']
            shell_string = shell.split('/')[2] if 'bash' in shell or 'zsh' in shell else None
            if not shell_string:
                utils.out(None, 'setup', 'E', 'Please use a bash or zsh shell to install the command system-wide')
            else:
                rc_file = f'.{shell_string}rc'
                read_rc = None
                if utils.exists(f'{home}/{rc_file}'):
                    with open(f'{home}/{rc_file}', 'r') as read_rc:
                        read_rc = read_rc.read()

                with open(f'{home}/{rc_file}', 'a') as write_rc:
                    write = True
                    if read_rc:
                        if 'bumsave' in read_rc:
                            write = False
                            utils.out(None, 'setup', 'I', 'Alias function already installed')
                    if write:
                        write_rc.write('\n')
                        write_rc.write(alias_function)
                        utils.out(None, 'setup', 'I', f'Alias added to {rc_file}')

        # Run pip to install the required modules
        # TODO: See how to generate a venv automatically through the code
        # subprocess.check_call([sys.executable, '-m', 'pip', 'install', f'{setup_folder}requirements.txt'])

    else:
        utils.out(None, 'setup', 'E', 'This system is not supported')
        exit()


if __name__ == '__main__':
    setup()
