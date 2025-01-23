"""Backup script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the GNU Affero General Public License v3.0
"""

import click
from click.core import ParameterSource
from tools.state import (
    state,
    set_state,
    append_state,
    incr_state,
    get_printed,
    force_verbose,
    activate_headless
)
from tools.utils import (
    get_app_details,
    get_setup_fld,
    is_archive,
    get_settings
)
from tools.piputils import (
    print_term,
    upload_archive,
    time_until_expiry,
)
from tools.scan import (
    frameworks_processing,
    vanilla_processing
)
from tools import utils
from os.path import exists
from signal import signal, SIGINT
from zipfile import ZipFile, ZIP_DEFLATED
import threading
import re
import os
import sys
import shutil
import time
import json


# Main logic & functions

def auto_detect(proj_fld):
    """Auto-detects the project language/framework
    to then back it up while applying the exclusions defined in the rule that
    matched for this particular language/framework
    :return: dictionary/object representing the rule/language corresponding to the project
    """
    v_leads = []
    fw_leads = []
    recent_rules = {'frameworks': [], 'vanilla': []}
    history_types = ('frameworks', 'vanilla')
    started = time.time()

    # Step 1: Get the rules from the config & temporary file
    try:
        with open(f'{get_setup_fld()}/config/rules.json', 'r') as read_file:
            rules = json.load(read_file)
    except FileNotFoundError:
        print_term('scan', 'E', 'rules.json not found', )
        exit(1)

    try:
        with open(f'{get_setup_fld()}/tmp/rules_history.json', 'r') as read_tmp:
            tmp_file = json.load(read_tmp)
        # If the rules history hasn't been checked yet, only keep the rules that are mentioned in the tmp file
        # The history file only contains the name of the rules that have been recently used by shlerp.
        # Before the scan, we need to know how the rules that are listed in the history file are actually built.
        for h_type in history_types:
            if len(tmp_file[h_type]) > 0:
                for rule in rules[h_type]:
                    for tmp_entry in tmp_file[h_type]:
                        if tmp_entry == rule['name']:
                            recent_rules[h_type].append(rule)

    except FileNotFoundError:
        print_term('scan', 'I', 'Temp file not found, will use the whole ruleset instead', )
        tmp_file = {'frameworks': [], 'vanilla': []}
        tmp_fld = f'{get_setup_fld()}/tmp'
        if not exists(tmp_fld):
            os.mkdir(tmp_fld)
        with open(f'{tmp_fld}/rules_history.json', 'w') as write_tmp:
            write_tmp.write(json.dumps(tmp_file, indent=4))

    # Step 2: Evaluate rules from the frameworks section
    print_term('scan', 'I', 'Evaluating framework rules...', )
    fw_leads = frameworks_processing(rules, proj_fld)

    # Step 3: Evaluate vanilla rules if the frameworks didn't match anything
    print_term('scan', 'I', 'Evaluating vanilla rules...', )
    v_leads = vanilla_processing(rules, proj_fld, )

    # Step 4: Exit the function
    elapsed_time = time.time() - started  # Calculate elapsed time
    if state('debug'): print_term('scan:stat', 'D', f'Auto-detection completed in {elapsed_time:.2f} seconds')
    return fw_leads + v_leads


def make_archive(proj_fld, dst_path, rules, options, uid, started, count):
    """
    Creates a zip archive of the project folder.
    :param proj_fld: text, the folder we want to archive
    :param dst_path: text, the location where we want to store the archive
    :param rules: list of dictionaries/objects representing the rules/languages corresponding to the project
    :param options: dictionary/object containing exclusion options
    :param uid: text representing a short uid
    :param started: number representing the time when the script has been executed
    :param count: string that represents nothing or the current count out of a total of backups to process
    """
    with ZipFile(f'{dst_path}.zip', 'w', ZIP_DEFLATED, compresslevel=9) as zip_archive:
        fld_count = file_count = 0
        success = True
        if state('total') == 1:
            count = ''
        
        #####################
        # Exclusion zone

        # Collect exclusions from all rules
        exclusions = {
            'files': set(),
            'folders': set(),
            'dep_folders': set()
        }
        exclusions['files'].add('.DS_Store')
        for rule in rules:
            if 'actions' in rule and 'exclude' in rule['actions']:
                exclude = rule['actions']['exclude']
                if 'files' in exclude:
                    exclusions['files'].update(exclude['files'])
                if 'folders' in exclude:
                    exclusions['folders'].update(exclude['folders'])
                if 'dep_folders' in exclude:
                    exclusions['dep_folders'].update(exclude['dep_folders'])

        for elem_path in utils.iglob_hidden(proj_fld + '/**', recursive=True):
            rel_name = elem_path.split(f'{proj_fld}/')[1]
            proceed = True
            output = True

            if options['nogit']:
                exclusions['folders'].add('.git')
                exclusions['files'].add('.gitignore')

            # Reject the current relative path if one of these conditions are matched
            if not options['noexcl']:
                if any(dep_folder in elem_path for dep_folder in exclusions['dep_folders']):
                    proceed = False
                if any(excl in rel_name for excl in exclusions['folders']):
                    proceed = False
                if any(excl in rel_name for excl in exclusions['files']):
                    proceed = False

            if '.git' in elem_path:
                output = False

            #####################
            # Archive making

            if proceed:
                if rel_name == '':
                    output = False
                try:
                    zip_archive.write(elem_path, rel_name)
                    if os.path.isdir(elem_path):
                        rel_name = rel_name + '/'
                        fld_count += 1
                    else:
                        file_count += 1
                    if output:
                        print_term('arch', 'I', f'Added: {rel_name}', uid, cnt=count)
                except Exception as e:
                    success = False
                    print_term('arch', 'E', f'Error adding {rel_name}: {e}', uid, cnt=count)

        if success:
            append_state('backed_up', proj_fld)
            print_term('stat', 'I', f'Folders: {fld_count} - Files: {file_count}', uid, cnt=count)
            print_term('stat', 'I', f'✅ Project archived ({"%.2f" % (time.time() - started)}s): {dst_path}.zip', uid, cnt=count)
        else:
            append_state('failures', proj_fld)
            print_term('stat', 'W', f'Incomplete archive: {dst_path}.zip', uid, cnt=count)


def duplicate(proj_fld, dst, rules, options, uid, started, count):
    """Duplicates a project folder, processes all files and folders. node_modules will be processed last if cache = True
    :param proj_fld: string that represents the project folder we want to duplicate
    :param dst: string that represents the destination folder where we will copy the project files
    :param rules: list of dictionaries/object representing the technologies used by the project
    :param options: dictionary/object containing exclusion options
    :param uid: text representing a short uid,
    :param started: number representing the time when the script has been executed
    :param count: string that represents nothing or the current count out of a total of backups to process
    """

    fld_count = file_count = 0
    elem_list = utils.get_files(proj_fld, rules, options)
    if state('total') == 1:
        count = ''
    os.mkdir(dst)
    for elem in elem_list:
        orig = f'{proj_fld}/{elem}'
        full_dst = f'{dst}/{elem}'
        try:
            if os.path.isdir(orig):
                shutil.copytree(orig, full_dst)
                if exists(full_dst):
                    print_term('copy', 'I', f'Done: {proj_fld}/{elem}/', uid, cnt=count)
                    fld_count += 1
            else:
                shutil.copy(orig, full_dst)
                file_count += 1
                if exists(full_dst):
                    print_term('copy', 'I', f'Done: {proj_fld}/{elem}', uid, cnt=count)
        except FileNotFoundError as fnf_error:
            print_term('copy', 'E', f'File not found: {fnf_error}', uid, cnt=count)
            append_state('failures', proj_fld)
        except PermissionError as perm_error:
            print_term('copy', 'E', f'Permission error: {perm_error}', uid, cnt=count)
            append_state('failures', proj_fld)
        except shutil.Error as shutil_error:
            print_term('copy', 'E', f'Shutil error: {shutil_error}', uid, cnt=count)
            append_state('failures', proj_fld)
        except Exception as exc:
            print_term('copy', 'E', f'Unexpected error: {exc}', uid, cnt=count)
            append_state('failures', proj_fld)

    print_term('stat', 'I', f'✅ Project duplicated ({"%.2f" % (time.time() - started)}s): {dst}/', uid, cnt=count)
    append_state('backed_up', proj_fld)


def set_upload_expiration(ctx, param, value):
    """Callback to fetch default expiration from settings.json if `-u` is used without a value."""
    opt_origin = ctx.get_parameter_source(param.name)
    # If the option as actually been used by the user
    if opt_origin == ParameterSource.COMMANDLINE:
        # Check if a value has actually been passed other than default.
        if value != 'default':
            return value
        else:
            # Load default from settings if no value provided
            return get_settings()['upload_default']['expiration']
    else:
        return None


def validate_path(ctx, param, value):
    """Custom validator to ensure the target exists."""
    if value:
        path = os.path.abspath(value)
        if exists(path):
            archive = True if is_archive(path) else False
            folder = True if os.path.isdir(path) else False
            return {
                'value': True,
                'exists': True,
                'path': path,
                'archive': archive,
                'folder': folder
            }
        else:
            return {
                'value': True,
                'exists': False,
                'path': path
            }
    else:
        return None


@click.command(epilog=f'shlerp v{get_app_details()["proj_ver"]} - More details: https://github.com/synka777/shlerp-cmd')
@click.option('-t', '--target', type=click.Path(), default=lambda: os.getcwd(), callback=validate_path, help=get_app_details()["options"]["target"])
@click.option('-o', '--output', type=click.Path(), callback=validate_path, help=get_app_details()["options"]["output"])
@click.option('-a', '--archive', default=False, is_flag=True, help=get_app_details()["options"]["archive"])
@click.option('-u', '--upload', callback=set_upload_expiration, help=get_app_details()["options"]["upload"])
@click.option('-r', '--rules', help=get_app_details()["options"]["rule"])
@click.option('-b', '--batch', default=False, is_flag=True, help=get_app_details()["options"]["batch"])
@click.option('-ne', '--noexcl', default=False, is_flag=True, help=get_app_details()["options"]["noexcl"])
@click.option('-ng', '--nogit', default=False, is_flag=True, help=get_app_details()["options"]["nogit"])
@click.option('-kh', '--keephidden', default=False, is_flag=True, help=get_app_details()["options"]["keephidden"])
@click.option('-hl', '--headless', default=False, is_flag=True, help=get_app_details()["options"]["headless"])
def main(target, output, archive, upload, rules, batch, noexcl, nogit, keephidden, headless):
    """Dev projects backups made easy"""

    #####################
    # Variables declaration

    exec_time = time.time()
    backup_sources = []
    archiving_failed = False
    bad_target = False
    options = {
        'noexcl': noexcl,
        'nogit': nogit,
        'keephidden': keephidden,
    }

    #####################
    # Options validation

    uid = utils.suid()
    set_state('uid', uid)

    if headless:
        activate_headless()

    paths = []
    def if_exists_add_key(param_dict, param_name):
        if param_dict:
            if param_dict.get('value', True):
                param_dict['opt'] = param_name
                paths.append(param_dict)
    if_exists_add_key(target, 'target')
    if_exists_add_key(output, 'output')

    for path in paths:
        if path['value']:
            if path['exists']:
                if path['archive']:
                    if path['opt'] == 'target':
                        if not upload:
                            bad_target = True
                    else:
                        bad_target = True
                else:
                    if not path['folder']:
                        bad_target = True
                if bad_target:
                    print_term('prep', 'E', f'The path provided for --{path["opt"]} is not a folder {path["path"]}', )
                    exit(0)
            else:
                print_term('prep', 'E', f'The provided target for --{path["opt"]} does not exist: {path["path"]}', )
                exit(0)
        else:
            print_term('prep', 'E', f'Missing value for --{path["opt"]}', )
            exit(0)

    if batch:
        force_verbose()
    if batch and not output:
        u_input = print_term('prep', 'W', 'You are about to backup your projects in the same folder. Continue (Y/N)? ',
                        uid,
                        input=True
                        )
        if u_input == 'N' or u_input == 'n':
            print_term('prep', 'I', 'Exiting shlerp', )
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
            print_term('prep', 'E', 'Supported regex format: ^[1-9]d*[y|Q|M|w|d|h|m|s]$ Tip: You can use -u without any value', )
            exit(0)

    #####################
    # Main logic

    def get_backup_sources(**kwargs):
        """Get the folder list to backup and scan each folder
        to determine the programming language/framework used
        """
        batch_list = []
        if batch:
            batch_list = [f'{target["path"]}/{f}' for f in os.listdir(target['path'])]
        else:
            batch_list.append(target['path'])

        for batch_elem in batch_list:
            elem_rules = None
            if os.path.isdir(batch_elem):
                if len(kwargs) > 0 and kwargs['rules']:
                    # Get rules from the --rule option, separated by semi colons
                    elem_rules = [rule for rule in kwargs['rule'].lower().split(';')]
                else:
                    if not batch_elem.startswith('.'):
                        print_term('scan', 'I', f'Scanning {batch_elem}', )
                        elem_rules = auto_detect(batch_elem, )
                if elem_rules:
                    print_term('scan', 'I', f'Detected: {[rule["name"] for rule in elem_rules]}', )
                    backup_sources.append({
                        'proj_fld': batch_elem,
                        'rules': elem_rules
                    })
                else:
                    print_term('scan', 'W', f'The folder {batch_elem} won\'t be processed as automatic rule detection failed')
                    append_state('ad_failures', batch_elem)
                    incr_state('total')
            if is_archive(batch_elem):
                if upload:
                    backup_sources.append({
                        'proj_fld': batch_elem,
                        'already_archived': True # already_archived will either be True, or non-existent at all
                    })

    ################################################
    # 1 - Check options validity & prepare mandatory
    #     variables for data processing

    if not rules:
        get_backup_sources()
    else:
        # If a --rule has been provided by the user, check if it is valid
        with open(f'{get_setup_fld()}/rules.json', 'r') as read_file:
            _rules = json.load(read_file)
            stored_rules = None
            for stored_rule in _rules:
                for rule in str(rule).lower().split(';'):
                    if str(rule).lower() == stored_rule['name'].lower():
                        stored_rules.append(stored_rule)
            if stored_rules:
                if batch:
                    get_backup_sources(rules=stored_rules)
                else:
                    backup_sources.append({
                        'proj_fld': target['path'],
                        'rules': stored_rules
                    })
                matched = True
            if not matched:
                print_term('scan', 'E', 'Rule name not found', )
                exit(0)

    # At this point we should have a list containing at least one project to process

    # If we don't have a particular output folder, use the same as the project
    if output:
        output = os.path.abspath(output['path'])
        for backup in backup_sources:
            project_name = backup['proj_fld'].split('/')[-1]
            backup['dst'] = f'{output}/{project_name}_{utils.get_dt()}'
    else:
        for backup in backup_sources:
            # If the current path to backup is already an archive, just set the  project folder as the backup dest.
            # The goal is for the rest of the code to just use backup['dst'] instead of using a condition 
            backup['dst'] = f'{backup["proj_fld"]}_{utils.get_dt()}' \
            if not backup.get('already_archived') \
            else backup['proj_fld']
    # At this point we should have the dst incorporated into the backup_job list

    ###################################
    # 2 - Data processing, show progress 
    if not state('debug'):
        incr_state('total', len(backup_sources))
        for backup in backup_sources:
            start_time = time.time()
            show_state = True if batch else False
            count = ''
            if show_state: # Used to display information
                count = f'{(len(state("backed_up")) + len(state("failures"))) + 1}/{state("total")}'

            if batch: # Used to display information
                print_term('arch' if archive else 'copy', 'I', f'Processing: {backup["proj_fld"]}', uid, cnt=count)

            if archive and not backup.get('already_archived'):
                # If --archive is provided to the script, we use make_archive()
                make_archive(
                    backup['proj_fld'], backup['dst'],
                    backup['rules'], options,
                    uid, start_time, count
                )
            if not archive:
                # Else if we don't want an archive we will do a copy of the project instead
                duplicate(
                    backup['proj_fld'], backup['dst'],
                    backup['rules'], options,
                    uid, start_time, count
                )

            if is_upload:
                step = 'uplo'
                zip_path = ''

                # The zip file name has to be defined differently depending if the --target was already an archive or not
                if backup.get('already_archived'):
                    zip_path = backup['dst']
                elif backup['proj_fld'] in state('backed_up'):
                    zip_path = f'{backup["dst"]}.zip'
                else:
                    print_term(step, 'E', 'Archiving process failed - skipping upload', )
                    archiving_failed = True

                if not archiving_failed:
                    archive_size_mb = utils.get_file_size(zip_path)
                    archive_size_gb = archive_size_mb / 1024  # Convert MB to GB
                    if archive_size_gb > 2:  # 2 GB limit
                        print_term(step, 'E', f'File size is too big: {archive_size_gb:.2f} GB', )
                    else:
                        response = upload_archive(zip_path, expiration)
                        json_resp = response.json()
                        if json_resp['success']:
                            expiry_message = time_until_expiry(json_resp['expires'])
                            print_term(step, 'I', f'🔗 Single use: {json_resp["link"]} - {expiry_message}', uid, cnt=count)
                        else:
                            append_state('upload_failures', backup['proj_fld'])
                            print_term(step, 'E', f'Upload failed: {json_resp["error"]}', uid, cnt=count)

            if batch:  # Used to display information
                failed_cnt = len(state('failures')) + len(state('ad_failures'))
                backed_up_cnt = len(state('backed_up'))

                # This condition is there to make sure we got through the whole list of projects
                # before displaying the stats
                if backed_up_cnt + failed_cnt == state('total'):
                    step = 'stat'
                    summary = f'Successful: {backed_up_cnt} - ' \
                            f'Failed: {failed_cnt} - ' \
                            f'Total runtime: {"%.2f" % (time.time() - exec_time)}s'
                    # Display which kind of operation has been done during current execution
                    operation = 'Upload' if upload else 'Archive' if archive else 'Copy'
                    print_term(step, 'I', summary, )
                    if len(state('ad_failures')) > 0:
                        print_term(step, 'W', f'Detection failures: {state("ad_failures")}', )
                    if len(state('failures')) > 0:
                        print_term(step, 'W', operation, f'Backup failures: {state("failures")}', )
                    if len(state('upload_failures')) > 0:
                        print_term(step, 'W', f'Upload failures: {state("upload_failures")}', )


def handle_sigint(signalnum, frame):
    print_term(get_printed()['step'], 'E', f'SIGINT: Interrupted by user', state('uid'))
    sys.exit()


if __name__ == '__main__':
    signal(SIGINT, handle_sigint)
    t = threading.Thread(target=main)
    t.start()
    t.join()
