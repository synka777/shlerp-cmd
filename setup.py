import os
from os import environ
from tools.utils import log, get_dt, req_installed, get_setup_fld
from os.path import join, exists
import subprocess
import platform
import venv
import pwd
import stat

def setup_print(step, lvl, message):
    """Standardizes the output format
    :param step, short string that indicates to the user the step we are going through
    :param lvl, letter that indicates if the displayed message is an Info, Warning or Error
    :param message, the message we want to print
    """
    log_type = 'exec'
    if step == 'setup':
        log_type = step
    if step == 'uninstall':
        log_type = step
    string = f"[{get_dt()}:{step}][{lvl}] {message}"
    log(string, log_type)
    print(string)


def get_file_owner(file_path):
    # try:
    # Get file stat
    file_stat = os.stat(file_path)
    # Get the UID (User ID) of the file owner
    uid = file_stat.st_uid
    # Convert UID to username
    owner_name = pwd.getpwuid(uid).pw_name
    
    return owner_name
    # except FileNotFoundError:
    #     return f"File not found: {file_path}"
    # except PermissionError:
    #     return f"Permission denied to access: {file_path}"


def setup():
    home = os.path.expanduser("~")
    setup_folder = get_setup_fld()
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
            rc_file_abs = f'{home}/{rc_file}'
            read_rc = None
            if exists(rc_file_abs):
                # If the owner is root, add write permissions to the members of the same group as root
                file_owner = get_file_owner(rc_file_abs)
                current_user = pwd.getpwuid(os.geteuid()).pw_name
                # Get file's metadata
                file_stat = os.stat(rc_file_abs)
                # Extract permission bits
                permissions = stat.S_IMODE(file_stat.st_mode)
                group_write = bool(permissions & stat.S_IWGRP)

                if (file_owner == 'root' or file_owner != current_user):
                    # Check if group is authorized to write on the file
                    if not group_write:
                        setup_print('setup', 'I', f'[1/2] Please enter password to edit {rc_file_abs}')
                        chmod_cmd = subprocess.Popen(['sudo', 'chmod', 'g+w', rc_file_abs])
                        chmod_cmd.wait()

                        if chmod_cmd.returncode != 0:
                            setup_print('setup', 'E', 'ERROR: Oops! Something happened, abort mission')
                            print(chmod_cmd.stderr.read())
                            exit(0)

                with open(rc_file_abs, 'r') as read_rc:
                    write = True
                    update = True
                    read_rc = read_rc.readlines()
                    source_line = f'source {setup_folder}/config/alias.sh'
                    filtered_lines = []
                    if read_rc:
                        for rc_line in read_rc:
                            # If we find a line that is already sourcing shlerp at any location
                            if rc_line.startswith('source') and ('shlerp' and '/alias.sh') in rc_line:
                                # Compare the location that's already sourced and the location from which we're running the new setup
                                # If we're running the setup from the same location as the one that's already sourced, do nothing
                                if rc_line == source_line:
                                    write = False
                                    setup_print('setup', 'I', '[1/2] OK: Alias function already installed')
                                    break
                            else:
                                filtered_lines.append(rc_line)

                        if write:
                            with open(rc_file_abs, 'w') as write_rc:
                                # Rewrite the entire file but replace the old sourced line by the new one
                                alias_op_str = 'Updated alias into' if update else 'Alias added to'
                                    
                                filtered_lines.append(source_line)
                                for filtered_line in filtered_lines:
                                    write_rc.write(filtered_line)
                                setup_print('setup', 'I', f'[1/2] OK: {alias_op_str} {rc_file}')

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

