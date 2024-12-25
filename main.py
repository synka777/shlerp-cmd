"""Backup script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the GNU Affero General Public License v3.0
"""

import click
from tools.utils import (
    get_app_details,
    get_setup_fld
)
from tools.pip.putils import (
    s_print,
    upload_archive,
    time_until_expiry,
)
from tools.core_tools import (
    frameworks_processing,
    vanilla_processing,
    prune_tried_rules
)
from tools import utils
from os.path import exists
from signal import signal, SIGINT
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import threading
import re
import os
import sys
import shutil
import time
import json


# Global variables

state = {
    'uid': '', # UID that represents the current execution. Not meant to be changed after its initial initialization
    'step': '', # Represents the step we're in, will be used if a SIGINT occurs
    'backed_up': [], # Lists successfully backed up projects path
    'failures': [], # Lists the projects that couldn't be backed up
    'ad_failures': [], # Lists the paths for which the autodetection failed
    'upload_failures': [], # Lists the paths for which the upload failed
    'total': 0 # Total number of projects to backup
}


# Main logic & functions

def auto_detect(proj_fld, uid):
    """Auto-detects the project language/framework
    to then back it up while applying the exclusions defined in the rule that
    matched for this particular language/framework
    :return: dictionary/object representing the rule/language corresponding to the project
    """
    global state
    v_leads = []
    fw_leads = []
    recent_rules = remaining_rules = {'frameworks': [], 'vanilla': []}
    history_types = ('frameworks', 'vanilla')
    framework_matched = False
    threshold_reached = False
    unclear = False
    threshold = 10  # Adapt it to match expected behavior
    state['step'] = 'scan'

    #####################
    # Step 1: Get the rules from the config & temporary file

    try:
        with open(f'{get_setup_fld()}/config/rules.json', 'r') as read_file:
            rules = json.load(read_file)
    except FileNotFoundError:
        s_print('scan', 'E', 'rules.json not found', uid)
        exit(1)

    try:
        with open(f'{get_setup_fld()}/tmp/rules_history.json', 'r') as read_tmp:
            tmp_file = json.load(read_tmp)
        # If the rules history hasn't been checked yet, only keep the rules that are mentioned in the tmp file
        # The history file only contains the name of the rules that have been rexently used by shlerp.
        # Before the scan, we need to know how the rules that are listed in the history file are actually built.
        for h_type in history_types:
            if len(tmp_file[h_type]) > 0:
                for rule in rules[h_type]:
                    for tmp_entry in tmp_file[h_type]:
                        if tmp_entry == rule['name']:
                            recent_rules[h_type].append(rule)

    except FileNotFoundError:
        s_print('scan', 'I', 'Temp file not found, will use the whole ruleset instead', uid)
        tmp_file = {'frameworks': [], 'vanilla': []}
        tmp_fld = f'{get_setup_fld()}/tmp'
        if not exists(tmp_fld):
            os.mkdir(tmp_fld)
        with open(f'{tmp_fld}/rules_history.json', 'w') as write_tmp:
            write_tmp.write(json.dumps(tmp_file, indent=4))

    #####################
    # Step 2: Evaluate rules from the frameworks section
    # It makes sense to try to match the frameworks first as they are more specific than the vanilla rules

    # 2-1: Using the history
    if len(recent_rules['frameworks']) > 0:
        s_print('scan', 'I', 'Evaluating framework history...', uid)
        fw_leads = frameworks_processing(recent_rules, proj_fld)
        if fw_leads:
            framework_matched = True

    # 2-2: Using the remaining framework rules that were not present into the history
    if not framework_matched:
        if len(recent_rules['vanilla']) > 0:
            # First we create a dict that only contains the remaining rules
            remaining_rules['frameworks'] = prune_tried_rules(rules, tmp_file, 'frameworks')
        else:
            remaining_rules = rules.copy()

        # Then do the pattern matching: those remaining rules
        s_print('scan', 'I', 'Evaluating framework rules...', uid)
        fw_leads = frameworks_processing(remaining_rules, proj_fld)

    if fw_leads:
        framework_matched = True
        if len(fw_leads) > 1:
            unclear = True

    if not framework_matched:

        #####################
        # Step 3: Evaluate vanilla rules if the frameworks didn't match anything

        # 3-1: Using the history
        if recent_rules:
            s_print('scan', 'I', 'Evaluating vanilla history...', uid)
            v_leads = vanilla_processing(recent_rules, threshold, proj_fld, uid)
            if len(v_leads) > 0:
                threshold_reached = True

        # 3-2: Using the whole ruleset
        if not threshold_reached:
            remaining_rules['vanilla'] = prune_tried_rules(rules, tmp_file, 'vanilla')
            s_print('scan', 'I', 'Evaluating vanilla rules...', uid)
            v_leads = vanilla_processing(remaining_rules, threshold, proj_fld, uid)

        if v_leads and len(v_leads) > 1:
            unclear = True

    #####################
    # Step 4: Exit the function

    if unclear:
        # If we have more than one language remaining it means the auto-detection wasn't successful
        s_print('scan', 'W', 'Unable to determine the main language for this project', uid)
        return None
    else:
        framework = True if fw_leads else False
        elected_rule = v_leads[0] if v_leads else fw_leads[0] if fw_leads else None
        if elected_rule:
            # Check if the history in the tmp file can be updated before exiting the function
            if not utils.history_updated(elected_rule, tmp_file, framework):
                s_print('scan', 'W', 'A problem occurred when trying to write in rules_history.json', uid)
            return elected_rule
        else:
            return None


def make_archive(proj_fld, dst_path, rule, options, uid, started, count):
    """Makes an archive of a given folder, without node_modules
    :param proj_fld: text, the folder we want to archive
    :param dst_path: text, the location where we want to store the archive
    :param rule: dictionary/object representing the rule/language corresponding to the project
    :param options: dictionary/object containing exclusion options
    :param uid: text representing a short uid
    :param started: number representing the time when the script has been executed
    :param count: string that represents nothing or the current count out of a total of backups to process
    """
    global state
    with ZipFile(f'{dst_path}.zip', 'w', ZIP_DEFLATED, compresslevel=9) as zip_archive:
        fld_count = file_count = symlink_count = 0
        success = False
        state['step'] = 'arch'
        if state['total'] == 1:
            count = ''
        for elem_name in utils.iglob_hidden(proj_fld + '/**', recursive=True):
            rel_name = elem_name.split(f'{proj_fld}/')[1]
            proceed = True
            output = True
            exclusions = rule['actions']['exclude']
            dep_folder = exclusions['dep_folder']
            if options['nogit']:
                exclusions['folders'].append('.git')
                exclusions['files'].append('.gitignore')

            #####################
            # Exclusion zone

            # Reject the current relative path if one of these conditions are matched
            if options['noexcl']:
                proceed = True
            else:
                if os.path.isdir(elem_name):
                    if dep_folder and dep_folder in rel_name:
                        proceed = False
                    if exclusions['folders']:
                        for fld_excl in exclusions['folders']:
                            if fld_excl in rel_name:
                                proceed = False
                else:
                    if exclusions['files']:
                        for file_excl in exclusions['files']:
                            if (
                                    file_excl == rel_name.split('/')[-1] or
                                    (dep_folder and dep_folder in rel_name)
                            ):
                                proceed = False
                    if exclusions['folders']:
                        for fld_excl in exclusions['folders']:
                            if fld_excl in rel_name:
                                proceed = False

            # Excludes all hidden files from the backup except git data
            path_chunks = elem_name.split('/')
            for chunk in path_chunks:
                if chunk.startswith('.'):
                    if not path_chunks[-1].startswith('.'):
                        output = False
                    if (
                            not options['keephidden'] and
                            not (
                                    chunk == '.git' or
                                    chunk == '.gitignore'
                            )
                    ):
                        proceed = False

            #####################
            # Archive making

            if proceed:
                if rel_name == '':
                    output = False
                # If the elem_name is actually a symbolic link, use zip_info and zipfile.writestr()
                # Source: https://gist.github.com/kgn/610907
                if os.path.islink(elem_name):
                    symlink_count += 1
                    # http://www.mail-archive.com/python-list@python.org/msg34223.html
                    zip_info = ZipInfo(elem_name)
                    zip_info.create_system = 3
                    # long type of hex val of '0xA1ED0000L',
                    # say, symlink attr magic...
                    zip_info.external_attr = 2716663808
                    try:
                        zip_archive.writestr(zip_info, os.readlink(f'{elem_name}'))
                        if output:
                            s_print('arch', 'I', f'Done: {rel_name}', uid, cnt=count)
                        success = True
                    except Exception as exc:
                        s_print('arch', 'E', f'A problem happened while handling {rel_name}: {exc}', uid, cnt=count)
                        state['failures'].append(proj_fld)
                else:
                    try:
                        zip_archive.write(f'{elem_name}', arcname=f'{rel_name}')
                        if os.path.isdir(elem_name):
                            fld_count += 1
                        else:
                            file_count += 1
                        if output:
                            s_print('arch', 'I', f'Done: {rel_name}', uid, cnt=count)
                        success = True
                    except Exception as exc:
                        s_print('arch', 'E', f'A problem happened while handling {rel_name}: {exc}', uid, cnt=count)
                        state['failures'].append(proj_fld)
        if success:
            state['backed_up'].append(proj_fld)
            s_print('arch', 'I', f'Folders: {fld_count} - Files: {file_count} - Symbolic links: {symlink_count}', uid, cnt=count)
            s_print('arch', 'I', f'✅ Project archived ({"%.2f" % (time.time() - started)}s): {dst_path}.zip', uid, cnt=count)
        else:
            state['failures'].append(proj_fld)
            s_print('arch', 'W', f'Incomplete archive: {dst_path}.zip', uid, cnt=count)


def duplicate(proj_fld, dst, rule, options, uid, started, count):
    """Duplicates a project folder, processes all files and folders. node_modules will be processed last if cache = True
    :param proj_fld: string that represents the project folder we want to duplicate
    :param dst: string that represents the destination folder where we will copy the project files
    :param rule: dictionary/object representing the rule/language corresponding to the project
    :param options: dictionary/object containing exclusion options
    :param uid: text representing a short uid,
    :param started: number representing the time when the script has been executed
    :param count: string that represents nothing or the current count out of a total of backups to process
    """
    global state
    try:
        state['step'] = 'copy'
        fld_count = file_count = symlink_count = 0
        exclusions = rule['actions']['exclude']
        elem_list = utils.get_files(proj_fld, exclusions, options)
        if state['total'] == 1:
            count = ''
        os.mkdir(dst)
        for elem in elem_list:
            orig = f'{proj_fld}/{elem}'
            full_dst = f'{dst}/{elem}'
            if os.path.isdir(orig):
                shutil.copytree(orig, full_dst, symlinks=True)
                if exists(full_dst):
                    s_print('copy', 'I', f'Done: {proj_fld}/{elem}', uid, cnt=count)
                    fld_count += 1
            else:
                shutil.copy(orig, full_dst)
                if os.path.islink(elem):
                    symlink_count += 1
                else:
                    file_count += 1
                if exists(full_dst):
                    s_print('copy', 'I', f'Done: {proj_fld}/{elem}', uid, cnt=count)

        s_print('copy', 'I', f'✅ Project duplicated ({"%.2f" % (time.time() - started)}s): {dst}/', uid, cnt=count)
        dep_folder = exclusions["dep_folder"]
        if options['dependencies'] and exists(f'{proj_fld}/{dep_folder}'):
            start_dep_folder = time.time()
            s_print('copy', 'I', f'Processing {dep_folder}...', uid, cnt=count)
            shutil.copytree(f'{proj_fld}/{dep_folder}', f'{dst}/{dep_folder}', symlinks=True)
            s_print('copy', 'I', f'Done ({"%.2f" % (time.time() - start_dep_folder)}s): {dst}/{dep_folder}/', uid, cnt=count)
            state['backed_up'].append(proj_fld)
        else:
            state['backed_up'].append(proj_fld)
    except Exception as exc:
        s_print('copy', 'E', f'during the duplication {exc}', uid, cnt=count)
        state['failures'].append(proj_fld)


@click.command(epilog=f'shlerp v{get_app_details()["proj_ver"]} - More details: https://github.com/synka777/shlerp-cmd')
@click.option('-p', '--path', type=click.Path(), help=get_app_details()["options"]["path"])
@click.option('-o', '--output', type=click.Path(), help=get_app_details()["options"]["output"])
@click.option('-a', '--archive', default=False, is_flag=True, help=get_app_details()["options"]["archive"])
@click.option('-u', '--upload', help=get_app_details()["options"]["upload"])
@click.option('-r', '--rule', help=get_app_details()["options"]["rule"])
@click.option('-b', '--batch', default=False, is_flag=True, help=get_app_details()["options"]["batch"])
@click.option('-d', '--dependencies', default=False, is_flag=True, help=get_app_details()["options"]["dependencies"])
@click.option('-ne', '--noexcl', default=False, is_flag=True, help=get_app_details()["options"]["noexcl"])
@click.option('-ng', '--nogit', default=False, is_flag=True, help=get_app_details()["options"]["nogit"])
@click.option('-kh', '--keephidden', default=False, is_flag=True, help=get_app_details()["options"]["keephidden"])
def main(path, output, rule, upload, dependencies, noexcl, nogit, keephidden, batch, archive):
    """Dev projects backups made easy"""

    #####################
    # Variables declaration

    exec_time = time.time()
    curr_fld = None
    missing_value = False
    backup_sources = []
    options = {
        'dependencies': dependencies,
        'noexcl': noexcl,
        'nogit': nogit,
        'keephidden': keephidden,
    }
    global state

    #####################
    # Options validation

    # Extended validation for the options that have a Click.path() type
    for opt in (('path', path), ('output', output)):
        if opt[1]:
            if not opt[1].startswith('-'):
                if opt[0] == 'path':
                    curr_fld = os.path.abspath(opt[1])
            else:
                s_print('prep', 'E', f'Missing value for {opt[0]}', uid)
                missing_value = True
    if missing_value:
        exit(0)
    if not path:
        curr_fld = os.getcwd()

    uid = utils.suid()
    state['uid'] = uid
    state['step'] = 'prep'
    if batch and not output:
        u_input = s_print('prep', 'W', 'You are about to backup your projects in the same folder. Continue (Y/N)? ',
                        uid,
                        input=True
                        )
        if u_input == 'N' or u_input == 'n':
            s_print('prep', 'I', 'Exiting shlerp', uid)
            exit(0)

    is_upload = False
    if upload:
        try:
            if re.compile('^[1-9]d*[y|Q|M|w|d|h|m|s]$').match(upload):
                archive = True
                expiration = upload
                is_upload = True
            else:
                raise ValueError
        except (TypeError, ValueError):
            s_print('prep', 'E', 'Supported regex format: ^[1-9]d*[y|Q|M|w|d|h|m|s]$ Tip: You can use -u without any value', uid)
            exit(0)

    #####################
    # Main logic

    def get_sources(**kwargs):
        """Get the folder list to backup and scan each folder
        to determine the programming language/framework used
        """
        batch_list = []
        if batch:
            batch_list = [f'{curr_fld}/{f}' for f in os.listdir(curr_fld)]
        else:
            batch_list.append(curr_fld)

        for batch_elem in batch_list:
            elem_rule = None
            if os.path.isdir(batch_elem):
                if len(kwargs) > 0 and kwargs['rule']:
                    elem_rule = kwargs['rule']
                else:
                    if not batch_elem.startswith('.'):
                        s_print('scan', 'I', f'Scanning {batch_elem}', uid)
                        elem_rule = auto_detect(batch_elem, uid)
                if elem_rule:
                    s_print('scan', 'I', f'Detected: {elem_rule["name"]}', uid)
                    backup_sources.append({
                        'proj_fld': batch_elem,
                        'rule': elem_rule
                    })
                else:
                    s_print('scan', 'W',
                            f'The folder {batch_elem} won\'t be processed as automatic rule detection failed',
                            uid)
                    state['ad_failures'].append(batch_elem)
                    state['total'] += 1

    ################################################
    # 1 - Check options validity & prepare mandatory
    #     variables for data processing

    if not rule:
        get_sources()
    else:
        # If a --rule has been provided by the user, check if it is valid
        with open(f'{get_setup_fld()}/rules.json', 'r') as read_file:
            rules = json.load(read_file)
            match = False
            for stored_rule in rules:
                if stored_rule['name'].lower() == str(rule).lower():
                    if batch:
                        get_sources(rule=stored_rule)
                    else:
                        backup_sources.append({
                            'proj_fld': curr_fld,
                            'rule': stored_rule
                        })
                    match = True
            if not match:
                s_print('scan', 'E', 'Rule name not found', uid)
                exit(0)

    # At this point we should have a list containing at least one project to process

    # If we don't have a particular output folder, use the same as the project
    if output:
        output = os.path.abspath(output)
        for backup in backup_sources:
            project_name = backup['proj_fld'].split('/')[-1]
            backup['dst'] = f'{output}/{project_name}_{utils.get_dt()}'
    else:
        for backup in backup_sources:
            backup['dst'] = f'{backup["proj_fld"]}_{utils.get_dt()}'
    # At this point we should have the dst incorporated into the backup_job list

    ####################################
    # 2 - Data processing, show progress 

    state['total'] += len(backup_sources)
    for backup in backup_sources:
        start_time = time.time()
        show_state = [True if state['total'] > 1 else False]
        count = ''
        if show_state: # Used to display information
            count = f'{(len(state['backed_up']) + len(state["failures"]))+1}/{state["total"]}'

        if batch: # Used to display information
            s_print('arch' if archive else 'copy', 'I', f'Processing: {backup["proj_fld"]}', uid, cnt=count)

        if archive:
            # If --archive is provided to the script, we use make_archive()
            make_archive(
                backup['proj_fld'], backup['dst'],
                backup['rule'], options,
                uid, start_time, count
            )
        else:
            # Else if we don't want an archive we will do a copy of the project instead
            duplicate(
                backup['proj_fld'], backup['dst'],
                backup['rule'], options,
                uid, start_time, count
            )

        if is_upload:
            step = 'uplo'
            state['step'] = step
            if backup['proj_fld'] in state['backed_up']:
                archive_size_mb = utils.get_file_size(f'{backup["dst"]}.zip')
                archive_size_gb = archive_size_mb / 1024  # Convert MB to GB
                if archive_size_gb > 2:  # 2 GB limit
                    s_print(step, 'E', f'File size is too big: {archive_size_gb:.2f} GB', uid)
                else:
                    response = upload_archive(f'{backup["dst"]}.zip', expiration)
                    json_resp = response.json()
                    if json_resp['success']:
                        expiry_message = time_until_expiry(json_resp['expires'])
                        s_print(step, 'I', f'🔗 Single use: {json_resp["link"]} - {expiry_message}', uid)
                    else:
                        state['upload_failures'].append(backup['proj_fld'])
                        s_print(step, 'E', f'Upload failed: {json_resp["error"]}', uid)
            else:
                s_print(step, 'E', 'Archiving process failed - skipping upload', uid)

        if batch:  # Used to display information
            failed_cnt = len(state['failures']) + len(state['ad_failures'])
            backed_up_cnt = len(state['backed_up'])

            # This condition is there to make sure we got through the whole list of projects
            # before displaying the stats
            if backed_up_cnt + failed_cnt == state['total']:
                step = state['step']
                summary = f'Successful: {backed_up_cnt}, - ' \
                        f'Failed: {failed_cnt}, - ' \
                        f'Total runtime: {'%.2f' % (time.time() - exec_time)}s'
                # Display which kind of operation has been done during current execution
                operation = 'Upload' if upload else 'Archive' if archive else 'Copy'
                s_print(step, 'I', summary, uid)
                if len(state['ad_failures']) > 0:
                    s_print(step, 'W', f'Detection failures: {state['ad_failures']}', uid)
                if len(state['failures']) > 0:
                    s_print(step, 'W', operation, f'Backup failures: {state['failures']}', uid)
                if len(state['upload_failures']) > 0:
                    s_print(step, 'W', f'Upload failures: {state['upload_failures']}', uid)


def handle_sigint(signalnum, frame):
    s_print(state['step'], 'E', f'SIGINT: Interrupted by user', state['uid'])
    sys.exit()


if __name__ == '__main__':
    signal(SIGINT, handle_sigint)
    t = threading.Thread(target=main)
    t.start()
    t.join()
