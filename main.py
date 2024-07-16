"""Backup script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the GNU Affero General Public License v3.0
"""
import utils
import os
import shutil
from os.path import exists
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import time
import click
from click import echo
from utils import s_print
import json

res_state = {
    'total': 0,
    'done': 0,
    'failed': 0,
    'failures': [],
    'ad_failures': []
}


def auto_detect(proj_fld, settings, uid):
    leads = []
    tried_history = False
    tried_all = False
    while True:
        # Try...Except
        try:
            with open(f'{os.getcwd()}/rules.json', 'r') as read_file:
                rules = json.load(read_file)
        except FileNotFoundError:
            s_print('scan', 'E', 'rules.json not found', uid)
            exit(1)
        # If the rules history hasn't been checked yet, only keep the rules that are mentioned in the tmp file
        if not tried_history:
            try:
                with open(f'{os.getcwd()}/tmp.json', 'r') as read_tmp:
                    tmp_file = json.load(read_tmp)
                    rules_history = tmp_file['rules_history']
                    for rule in rules:
                        if rule['name'] not in rules_history:
                            current_pos = rules.index(rule)
                            rules.pop(current_pos)
            except (FileNotFoundError, ValueError):
                s_print('scan', 'I', 'Temp file not found, will use the whole ruleset instead', uid)
                tmp_file = {'rules_history': []}
                with open(f'{os.getcwd()}/tmp.json', 'w') as write_tmp:
                    write_tmp.write(json.dumps(tmp_file, indent=4))
                tried_history = True
        else:
            to_prune = []
            for rule_name in rules_history:
                for rule in rules:
                    if rule['name'] == rule_name:
                        to_prune.append(rule)
            for junk in to_prune:
                rules.remove(junk)

        for rule in rules:
            extensions = []
            total = 0
            for file in rule['detect']['files']:
                names = file['name']
                pattern = file['pattern']
                if len(names) == 1:
                    # If only one extension, add it to the extension array
                    if names[0].startswith('*.'):
                        extensions.append({
                            'name': names[0],
                            'weight': file['weight']
                        })
                    else:
                        # If only one filename check if it exists, then check its content
                        filename = names[0]
                        if exists(f'{proj_fld}/{filename}'):
                            # If the pattern defined in the rule is not set to null, search it in the file
                            if pattern:
                                with open(f'{proj_fld}/{filename}', 'r') as file_content:
                                    if pattern in file_content:
                                        total += file['weight']
                            else:
                                total += file['weight']
                if len(names) > 1:
                    for name in names:
                        if name.startswith('*.'):
                            extensions.append({
                                'name': name,
                                'weight': file['weight']
                            })
                        else:
                            # If the filename is not an extension, check for its existence right away
                            if exists(f'{proj_fld}/{name}'):
                                total += file['weight']

            for folder in rule['detect']['folders']:
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
            rule["total"] = total
            rule["extensions"] = extensions
            leads.append(rule)

        crawled = False
        if utils.weight_found(leads):
            leads = utils.elect(leads)
        else:
            # If the main method we use to find weight (filename matching) hasn't matched anything
            # Use iglob to match files that have a given extension and update the weights
            leads = utils.crawl_for_weight(proj_fld, leads)
            crawled = True
            if utils.weight_found(leads):
                leads = utils.elect(leads)

        # If weight have been found BUT we have multiple winners, search for more weight
        if utils.weight_found(leads) and len(leads) > 1:
            if not crawled:
                s_print('scan', 'I', 'Crawling...', uid)
                leads = utils.crawl_for_weight(proj_fld, leads)

        if not tried_history:
            tried_history = True
        else:
            tried_all = True

        # Final checks before finishing the current iteration in the loop
        if len(leads) > 1:
            # If we have more than one language remaining it means the auto-detection wasn't successful
            leads = list([])
            if tried_all:
                s_print('scan', 'W', 'Unable to determine the main language for this project', uid)
                break
            else:
                s_print('scan', 'I', 'Trying the whole ruleset...', uid)
                # Ah shit, here we go again
        else:
            if utils.weight_found(leads):
                # Successful exit point
                # Check if the history in the tmp file can be updated before breaking out of the loop
                if not utils.history_updated(leads[0], settings, tmp_file):
                    s_print('scan', 'I', 'A problem occurred when trying to write in tmp.json', uid)
                    break
                else:
                    break
            else:
                leads = list([])
                if tried_all:
                    break
                # Ah shit, here we go again
    return leads[0] if leads else False


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
        if res_state['total'] == 1:
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
                        res_state['failures'].append(proj_fld)
                        return utils.update_res_state(res_state, 1)
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
                        res_state['failures'].append(proj_fld)
                        return utils.update_res_state(res_state, 1)
        if success:
            s_print('arch', 'I', f'Folders: {fld_count} - Files: {file_count} - Symbolic links: {symlink_count}', uid, cnt=count)
            s_print('arch', 'I', f'✅ Project archived ({"%.2f" % (time.time() - started)}s): {dst_path}.zip', uid, cnt=count)
            return utils.update_res_state(res_state, 0)
        else:
            s_print('arch', 'W', f'Incomplete archive: {dst_path}.zip', uid, cnt=count)
            res_state['failures'].append(proj_fld)
            return utils.update_res_state(res_state, 1)


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
        fld_count = file_count = symlink_count = 0
        exclusions = rule['actions']['exclude']
        elem_list = utils.get_files(proj_fld, exclusions, options)
        if res_state['total'] == 1:
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
            return utils.update_res_state(res_state, 0)
        else:
            return utils.update_res_state(res_state, 0)
    except Exception as exc:
        s_print('copy', 'E', f'during the duplication {exc}', uid, cnt=count)
        res_state['failures'].append(proj_fld)
        return utils.update_res_state(res_state, 1)


@click.command()
@click.option('-p', '--path', type=click.Path(),
              help='The path of the project we want to backup.')
@click.option('-o', '--output', type=click.Path(),
              help='The location where we want to store the backup')
@click.option('-r', '--rule',
              help='Manually specify a rule name if you want to skip the language detection process')
@click.option('-d', '--dependencies', default=False,
              help='Includes the folders marked as dependency folders in the duplication. Only works when using -a',
              is_flag=True)
@click.option('-ne', '--noexcl', default=False,
              help='Disables the exclusion system inherent to each rule',
              is_flag=True)
@click.option('-ng', '--nogit', default=False,
              help='Excludes git data from the backup',
              is_flag=True)
@click.option('-kh', '--keephidden', default=False,
              help='Excludes hidden files and folders from the backup but keeps git data',
              is_flag=True)
@click.option('-b', '--batch', default=False,
              help='This option will consider all the sub-folders from the cwd as repositories and process it one by one'
                   'This is especially useful to backup all your projects on an another location.',
              is_flag=True)
@click.option('-a', '--archive', default=False,
              help='Archives the project folder instead of making a copy of it',
              is_flag=True)
def main(path, output, rule, dependencies, noexcl, nogit, keephidden, batch, archive):
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
    global res_state

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
    home = os.path.expanduser("~")
    os.chdir(f'{home}/.local/bin/shlerp/')

    with open(f'{os.getcwd()}/settings.json', 'r') as read_settings:
        settings = json.load(read_settings)
    uid = utils.suid()

    if batch and not output:
        u_input = s_print('prep', 'W', 'You are about to backup your projects in the same folder. Continue (Y/N)? ',
                          uid,
                          input=True
                          )
        if u_input == 'N' or u_input == 'n':
            s_print('prep', 'I', 'Exiting shlerp', uid)
            exit(0)

    #####################
    # Main logic

    def get_sources(**kwargs):
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
                        elem_rule = auto_detect(batch_elem, settings, uid)
                if elem_rule:
                    backup_sources.append({
                        'proj_fld': batch_elem,
                        'rule': elem_rule
                    })
                else:
                    s_print('scan', 'W',
                            f'The folder {batch_elem} won\'t be processed as automatic rule detection failed',
                            uid)
                    res_state.update(utils.update_res_state(res_state, 1))
                    res_state['ad_failures'].append(batch_elem)
                    res_state['total'] += 1
        echo('------------')

    if not rule:
        get_sources()
    else:
        # If a --rule has been provided by the user, check if it is valid
        with open(f'{os.getcwd()}/rules.json', 'r') as read_file:
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

    res_state['total'] += len(backup_sources)
    for backup in backup_sources:
        start_time = time.time()
        show_res_state = [True if res_state['total'] > 1 else False]
        count = ''
        if show_res_state:
            count = f'{res_state["done"] + res_state["failed"]}/{res_state["total"]}'
        # payload = {
        #     'source': backup['proj_fld'], 'dest': backup['dst'],
        #     'rule': backup['rule'], 'options': options,
        #     'uid': uid, 'start_time': start_time,
        #     'res_state': res_state
        # }
        if batch:
            s_print('arch' if archive else 'copy', 'I', f'Processing: {backup["proj_fld"]}', uid, cnt=count)
        if archive:
            # If --archive is provided to the script, we use make_archive()
            res_state = make_archive(
                backup['proj_fld'], backup['dst'],
                backup['rule'], options,
                uid, start_time, count
            )
            # res_state = make_archive(payload)

        else:
            # Else if we don't want an archive we will do a copy of the project instead
            res_state = duplicate(
                backup['proj_fld'], backup['dst'],
                backup['rule'], options,
                uid, start_time, count
            )
            # res_state = duplicate(payload)

        if batch:
            echo('------------')
            if res_state['done'] + res_state['failed'] == res_state['total']:
                res_stateary = f'Successful: {res_state["done"]}, - ' \
                          f'Failed: {res_state["failed"]}, - ' \
                          f'Total runtime: {"%.2f" % (time.time() - exec_time)}s'
                operation = 'arch' if archive else 'copy'
                s_print(operation, 'I', res_stateary, uid)
                if res_state['failed'] > 0 and len(res_state['failures']) > 0:
                    s_print(operation, 'W', f'Operation failures: {res_state["failures"]}', uid)
                if len(res_state['ad_failures']) > 0:
                    s_print(operation, 'W', f'Detection failures: {res_state["ad_failures"]}', uid)


if __name__ == '__main__':
    main()
