import os
from os import environ
from tools.utils import log, get_dt, req_installed, get_settings
from os.path import join, exists
import platform
import venv


def setup_print(step, lvl, message, *args):
    """Standardizes the output format
    :param step, short string that indicates to the user the step we are going through
    :param lvl, letter that indicates if the displayed message is an Info, Warning or Error
    :param message, the message we want to print
    """
    uid = None
    log_type = 'exec'
    if step == 'setup':
        log_type = step
    if step == 'uninstall':
        log_type = step
    if len(args) > 0:
        uid = args[0]
    string = f"[{(f'{uid}:' if uid else '')}{get_dt()}:{step}][{lvl}] {message}"
    log(string, log_type)
    print(string)


def setup():
    home = os.path.expanduser("~")
    setup_folder = os.getcwd()

    current_os = platform.uname().system

    # Determine on which OS the script is running
    if current_os in ('Darwin', 'Linux'):
        # Step 1: Add the alias into .bashrc/.zshrc
        shell = environ['SHELL']
        shell_string = shell.split('/')[2] if 'bash' in shell or 'zsh' in shell else None
        if not shell_string:
            setup_print('setup', 'E', '[1/2] Please use a bash or zsh shell to install the command system-wide')
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
                        setup_print('setup', 'I', '[1/2] OK: Alias function already installed')
                if write:
                    write_rc.write(f'source {setup_folder}config/function.template')
                    setup_print('setup', 'I', f'[1/2] OK: Alias added to {rc_file}')

        def check_deps(first_try):
            word = 'successfully'
            if not first_try:
                word = 'already'
            if req_installed(setup_folder):
                setup_print('setup', 'I', f'[2/2] OK: Virtual environment {word} installed')
                setup_print('setup', 'I', f'✅ Install complete! Please restart your terminal to use the shlerp command')
            else:
                setup_print('setup', 'E', 'ERROR: A problem happened during the requirements installation')
                exit(0)
        # Step 2: Create a venv in the setup folder and install the requirements
        venv_folder = join(setup_folder, "venv")
        if not exists(venv_folder):
            venv.create(venv_folder, with_pip=True)
            # Then proceed with the requirements installation
            check_deps(True)
        else:
            check_deps(False)

    else:
        setup_print('setup', 'E', 'ERROR: Shell or system not supported')
        exit(0)


if __name__ == '__main__':
    setup()

