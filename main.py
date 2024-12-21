"""Backup script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the GNU Affero General Public License v3.0
"""
import click
from click import echo
from tools.utils import get_app_details, get_setup_fld
from tools.pip.putils import s_print, upload_archive
from tools.pip import putils
from tools import utils
from os.path import exists
from signal import signal
from signal import SIGINT
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
    'uid': '',  # UID that represents the current execution. Not meant to be changed after its initial initialization
    'step': '',  # Represents the step we're in, will be used if a SIGINT occurs
    'total': 0,
    'done': [],
    'failed': [],
    'failures': [],
    'ad_failures': []
}

# Main logic & functions


def auto_detect(proj_fld, uid):
    v_leads = []
    fw_leads = []
    recent_rules = remaining_rules = {'frameworks': [], 'vanilla': []}
    history_names = ('frameworks', 'vanilla')
    framework_matched = False
    threshold_reached = False
    unclear = False
    threshold = 10  # Adapt it to match expected behavior
    state['step'] = 'scan'

    def frameworks_processing(_rules):
        _fw_leads = []
        for _rule in _rules['frameworks']:
            total = 0
            # Compare the files found into the project with the files that are defined into the current rule.
            # If both are the same, then it's a match. In this case, add score (weight) for the current rule.
            for file in _rule['detect']['files']:
                names = file['names']
                pattern = file['pattern']
                if len(names) == 1:
                    # If only one filename check if it exists, then check its content
                    filename = names[0]
                    if exists(f'{proj_fld}/{filename}'):
                        # If the pattern defined in the rule is not set to null, search it in the file
                        if pattern:
                            with open(f'{proj_fld}/{filename}', 'r') as file_content:
                                if pattern in file_content.read():
                                    total += file['weight']
                        else:
                            total += file['weight']
                if len(names) > 1:
                    for name in names:
                        if exists(f'{proj_fld}/{name}'):
                            if pattern:
                                with open(f'{proj_fld}/{name}', 'r') as file_content:
                                    if pattern in file_content.read():
                                        total += file['weight']
                            else:
                                total += file['weight']

            # Then we compare the project sub-folders with the folders defined into the current _rule.
            for folder in _rule['detect']['folders']:
                name = folder['name']
                # We check if each folder from the current rule exists
                if exists(f'{proj_fld}/{name}/'):
                    # If we don't have any files to check in the folder, increment the rule weight
                    if not folder['files']:
                        total += folder['weight']
                    else:
                        # Make sure that each files from the folder element exists before increasing the weight
                        match = True
                        for file in folder['files']:
                            if not exists(f'{proj_fld}/{folder["name"]}/{file}'):
                                match = False
                        if match:
                            total += folder['weight']
            _rule["total"] = total
            # Calculates the threshold for the current rule
            rule_threshold = 0
            for file_then_fld in _rule['detect'].keys():
                for criteria in _rule['detect'][file_then_fld]:
                    rule_threshold += criteria['weight']
            # Then add the rule into the leads array if all of its criteria matched
            if _rule['total'] >= rule_threshold:
                _fw_leads.append(_rule)
        return putils.elect(_fw_leads)

    def vanilla_processing(_rules):
        s_print('scan', 'I', 'Crawling...', uid)
        leads = putils.crawl_for_weight(proj_fld, _rules['vanilla'])
        # If the weight of the rule that has the heaviest score is lighter than the threshold,
        # We empty the leads list
        _elected_rule = putils.elect(leads)
        if not _elected_rule:
            leads = list([])
        else:
            leads = list([]) if _elected_rule[0]['total'] < threshold else list([_elected_rule[0]])
        return leads

    def prune_tried_rules(_rules, _tmp_file, history_type):
        # We get a copy of the certain type of rules, let's say Vanilla rules for example.
        _remaining_rules = _rules[history_type].copy()
        for _rule_name in _tmp_file[history_type]:
            for _rule in _rules[history_type]:
                if _rule['name'] == _rule_name:
                    _remaining_rules.remove(_rule)
        return _remaining_rules

    #####################
    # Step 1: Get the rules from the config/temporary file

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
        for hist in history_names:
            if len(tmp_file[hist]) > 0:
                iter_rules = recent_rules = rules.copy()
                for rule in iter_rules[hist]:
                    for tmp_entry in tmp_file[hist]:
                        if re.search(f'\b{rule["name"]}\b', tmp_entry):
                            recent_rules[hist].remove(rule)
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

    # 2-1: Using the history
    if recent_rules:
        fw_leads = frameworks_processing(recent_rules)
        if fw_leads:
            framework_matched = True

    # 2-2: Using the remaining framework rules that were not present into the history
    if not framework_matched:
        if recent_rules:
            # First we create a dict that only contains the remaining rules
            remaining_rules['frameworks'] = prune_tried_rules(rules, tmp_file, 'frameworks')
        else:
            remaining_rules = rules.copy()

        # Then do the pattern matching against those remaining rules
        s_print('scan', 'I', 'Trying the whole ruleset...', uid)
        fw_leads = frameworks_processing(remaining_rules)

    if fw_leads:
        framework_matched = True
        if len(fw_leads) > 1:
            unclear = True

    if not framework_matched:

        #####################
        # Step 3: Evaluate vanilla rules if the frameworks didn't match anything

        # 3-1: Using the history
        if recent_rules:
            v_leads = vanilla_processing(recent_rules)
            if len(v_leads) > 0:
                threshold_reached = True

        # 3-2: Using the whole ruleset
        if not threshold_reached:
            remaining_rules['vanilla'] = prune_tried_rules(rules, tmp_file, 'vanilla')
            s_print('scan', 'I', 'Trying the whole ruleset...', uid)
            v_leads = vanilla_processing(remaining_rules)

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
            if not putils.history_updated(elected_rule, tmp_file, framework):
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
    with ZipFile(f'{dst_path}.zip', 'w', ZIP_DEFLATED, compresslevel=9) as zip_archive:
        fld_count = file_count = symlink_count = 0
        success = False
        state['step'] = 'arch'
        if state['total'] == 1:
            count = ''
        for elem_name in putils.iglob_hidden(proj_fld + '/**', recursive=True):
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
                        return putils.update_state(state, 1, proj_fld)
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
                        return putils.update_state(state, 1, proj_fld)
        if success:
            s_print('arch', 'I', f'Folders: {fld_count} - Files: {file_count} - Symbolic links: {symlink_count}', uid, cnt=count)
            s_print('arch', 'I', f'✅ Project archived ({"%.2f" % (time.time() - started)}s): {dst_path}.zip', uid, cnt=count)
            return putils.update_state(state, 0, proj_fld)
        else:
            s_print('arch', 'W', f'Incomplete archive: {dst_path}.zip', uid, cnt=count)
            state['failures'].append(proj_fld)
            return putils.update_state(state, 1, proj_fld)


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
    try:
        state['step'] = 'copy'
        fld_count = file_count = symlink_count = 0
        exclusions = rule['actions']['exclude']
        elem_list = putils.get_files(proj_fld, exclusions, options)
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
            # TODO: optimize the logic here
            # Try...Except
            start_dep_folder = time.time()
            s_print('copy', 'I', f'Processing {dep_folder}...', uid, cnt=count)
            shutil.copytree(f'{proj_fld}/{dep_folder}', f'{dst}/{dep_folder}', symlinks=True)
            s_print('copy', 'I', f'Done ({"%.2f" % (time.time() - start_dep_folder)}s): {dst}/{dep_folder}/', uid, cnt=count)
            return putils.update_state(state, 0, proj_fld)
        else:
            return putils.update_state(state, 0, proj_fld)
    except Exception as exc:
        s_print('copy', 'E', f'during the duplication {exc}', uid, cnt=count)
        state['failures'].append(proj_fld)
        return putils.update_state(state, 1, proj_fld)


@click.command(epilog=f'shlerp v{get_app_details()["proj_ver"]} - More details: https://github.com/synka777/shlerp-cmd')
@click.option('-p', '--path', type=click.Path(),
            help='The path of the project we want to backup. If not provided the current working directory will be backed up')
@click.option('-o', '--output', type=click.Path(),
            help='The location where we want to store the backup')
@click.option('-r', '--rule',
            help='Manually specify a rule name if you want to skip the language detection process')
@click.option(
            '-u', '--upload',
            help='Make an archive, upload it to file.io and get the download url. An optional validity period can be set following this pattern: ^[1-9]d*[y|Q|M|w|d|h|m|s]$')
@click.option('-d', '--dependencies', default=False,
            help='Include the folders marked as dependency folders in the duplication. Only works when using -a',
            is_flag=True)
@click.option('-ne', '--noexcl', default=False,
            help='Disable the exclusion system inherent to each rule',
            is_flag=True)
@click.option('-ng', '--nogit', default=False,
            help='Exclude git data from the backup',
            is_flag=True)
@click.option('-kh', '--keephidden', default=False,
            help='Include hidden files and folders in the backup (they are excluded by default, except for git-related ones)',
            is_flag=True)
@click.option('-b', '--batch', default=False,
            help='This option will consider all the sub-folders from the cwd as repositories and process it one by one'
                'This is especially useful to backup all your projects on an another location.',
            is_flag=True)
@click.option('-a', '--archive', default=False,
            help='Archive the project folder instead of making a copy of it',
            is_flag=True)
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
                echo(f'Error: Option \'--{opt[0]}\' requires an argument.')
                missing_value = True
    if missing_value:
        exit(0)
    if not path:
        curr_fld = os.getcwd()

    uid = putils.suid()
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
                    s_print('scan', 'I', f'Matching rule: {elem_rule["name"]}', uid)
                    backup_sources.append({
                        'proj_fld': batch_elem,
                        'rule': elem_rule
                    })
                else:
                    s_print('scan', 'W',
                            f'The folder {batch_elem} won\'t be processed as automatic rule detection failed',
                            uid)
                    state.update(putils.update_state(state, 1, batch_elem))
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
            backup['dst'] = f'{output}/{project_name}_{putils.get_dt()}'
    else:
        for backup in backup_sources:
            backup['dst'] = f'{backup["proj_fld"]}_{putils.get_dt()}'
    # At this point we should have the dst incorporated into the backup_job list

    ####################################
    # 2 - Data processing, show progress 

    state['total'] += len(backup_sources)
    for backup in backup_sources:
        start_time = time.time()
        show_state = [True if state['total'] > 1 else False]
        count = ''
        if show_state: # Used to display information
            count = f'{state["done"] + state["failed"]}/{state["total"]}'

        if batch: # Used to display information
            s_print('arch' if archive else 'copy', 'I', f'Processing: {backup["proj_fld"]}', uid, cnt=count)

        if archive:
            # If --archive is provided to the script, we use make_archive()
            state = make_archive(
                backup['proj_fld'], backup['dst'],
                backup['rule'], options,
                uid, start_time, count
            )
        else:
            # Else if we don't want an archive we will do a copy of the project instead
            state = duplicate(
                backup['proj_fld'], backup['dst'],
                backup['rule'], options,
                uid, start_time, count
            )

        if is_upload:
            step = 'uplo'
            if backup['proj_fld'] in state['done']:
                archive_size_mb = utils.get_file_size(f'{backup["dst"]}.zip')
                archive_size_gb = archive_size_mb / 1024  # Convert MB to GB
                if archive_size_gb > 2:  # 2 GB limit
                    s_print(step, 'E', f'File size is too big: {archive_size_gb:.2f} GB', uid)
                else:
                    response = upload_archive(f'{backup["dst"]}.zip', expiration)
                    json_resp = response.json()
                    if json_resp['success']:
                        expiry_message = putils.time_until_expiry(json_resp['expires'])
                        s_print(step, 'I', f'🔗 Single use: {json_resp["link"]} - {expiry_message}', uid)
                    else:
                        s_print(step, 'E', f'Upload failed: {json_resp["error"]}', uid)
            else:
                s_print(step, 'E', 'Archiving process failed - skipping upload', uid)

        if batch:  # Used to display information
            if len(state['done']) + len(state['failed']) == state['total']:
                summary = f'Successful: {state["done"]}, - ' \
                        f'Failed: {state["failed"]}, - ' \
                        f'Total runtime: {"%.2f" % (time.time() - exec_time)}s'
                # step = 'arch' if archive else 'copy'
                s_print(step, 'I', summary, uid)
                if state['failed'] > 0 and len(state['failures']) > 0:
                    s_print(step, 'W', f'step failures: {state["failures"]}', uid)
                if len(state['ad_failures']) > 0:
                    s_print(step, 'W', f'Detection failures: {state["ad_failures"]}', uid)


def handle_sigint(signalnum, frame):
    s_print(state['step'], 'E', f'SIGINT: Interrupted by user', state['uid'])
    sys.exit()


if __name__ == '__main__':
    signal(SIGINT, handle_sigint)
    t = threading.Thread(target=main)
    t.start()
    t.join()
