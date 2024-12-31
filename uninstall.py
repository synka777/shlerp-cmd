import os
from os import environ
from os.path import exists
from tools.piputils import print_term
from tools.utils import get_setup_fld
import sys
import subprocess


def uninstall():
    home = os.path.expanduser("~")
    setup_folder = get_setup_fld()

    shell = environ['SHELL']
    shell_string = shell.split('/')[2] if 'bash' in shell or 'zsh' in shell else None
    rc_file = f'.{shell_string}rc'
    rc_file_path = f'{home}/{rc_file}'

    # Step 1: Uninstall the function alias from the rc_file
    if exists(rc_file_path):
        with open(rc_file_path, 'r') as read_rc:
            double_check = True
            read_rc = read_rc.read()
            tmp_rc_path = f'{setup_folder}/.rc_file'
            source_line = f'source {setup_folder}/config/alias.sh'
            if source_line in read_rc:
                cleaned_rc = read_rc.replace(source_line, '')
                with open(tmp_rc_path, 'w') as write_tmp_rc:
                    write_tmp_rc.write(cleaned_rc)
                if exists(tmp_rc_path):
                    subprocess.run(["mv", tmp_rc_path, rc_file_path])
            else:
                double_check = False
                print_term('uninstall', 'I', f'[1/2] OK: Function not found in {rc_file}')

        if double_check:
            with open(rc_file_path, 'r') as read_rc:
                if source_line not in read_rc:
                    print_term('uninstall', 'I', f'[1/2] OK: Uninstalled the function from {rc_file}')
                else:
                    print_term('uninstall', 'E', f'[1/2] ERROR: Function still sourced in {rc_file}')

    # Step 2: Remove the installation folder
    subprocess.call([
        'sudo', 'rm', '-rf', f'{setup_folder}',
        '&&' f'{print_term("uninstall", "I", f"[2/2] OK: Uninstalled shlerp from {setup_folder}")}'
        'wait'
    ])
    sys.exit(0)


if __name__ == '__main__':
    uninstall()
