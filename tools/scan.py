###############################################################
# This file features the main functions that are used by the 
# rule detection system to scan the project and find out the
# language/framework context that is used in a particular project

from tools.state import state
from tools.piputils import print_term
import tools.utils as utils
from os.path import exists
import glob
import os
import re


def frameworks_processing(rules, proj_fld):
    """Process the project folder to detect frameworks based on the provided rules.
    :param rules: object list containing framework rules
    :param proj_fld: text, the folder we want to process
    :return: a list of matched framework rules
    """
    _fw_leads = []
    dep_folders = utils.get_dependency_folders(rules['frameworks'] + rules['vanilla'])
    for _rule in rules['frameworks']:
        exclusions = _rule['actions']['exclude']
        if state('debug'): print_term('scan:fram', 'D', f'Processing rule: {_rule["name"]}')
        total_matches = 0

        # Use os.walk() to traverse the project folder and its subfolders
        for root, dirs, files in os.walk(proj_fld):
            # Exclude dependency folders from dirs
            dirs[:] = [d for d in dirs if not excluded(os.path.join(root, d), exclusions, dep_folders)]

            # Check for folders defined in the rule
            for folder in _rule['detect']['folders']:
                name = folder['name']
                if name in dirs:
                    folder_path = os.path.join(root, name)
                    if not excluded(folder_path, exclusions, dep_folders):
                        if not folder['files']:
                            total_matches += 1
                            if state('debug'): print_term('scan:fram', 'D', f'Matched folder: {folder_path}')
                        else:
                            match = True
                            for file in folder['files']:
                                if not exists(os.path.join(folder_path, file)):
                                    match = False
                            if match:
                                total_matches += 1
                                if state('debug'): print_term('scan:fram', 'D', f'Matched all files in folder: {folder_path}')
                    else:
                        continue

            # Check for files defined in the rule
            for file in _rule['detect']['files']:
                names = file['names']
                pattern = file.get('pattern', None)
                for name in names:
                    if name in files:
                        file_path = os.path.join(root, name)
                        if not excluded(file_path, exclusions, dep_folders):
                            if pattern:
                                with open(file_path, 'r') as file_content:
                                    content = file_content.read()
                                    if re.search(pattern, content):
                                        total_matches += 1
                                        if state('debug'): print_term('scan:fram', 'D', f'Matched pattern in file: {file_path}')
                            else:
                                total_matches += 1
                                if state('debug'): print_term('scan:fram', 'D', f'Matched file: {file_path}')

        _rule["total"] = total_matches
        if state('debug'): print_term('scan:fram', 'D', f'Total score for rule {_rule["name"]}: {total_matches}')

        matches_expected_num = 0
        def get_matches_expected_num(type):
            matches_expected_num = 0
            excl_obj = _rule['actions']['exclude']
            exclusions = excl_obj[type]
            dep_folders = excl_obj.get('dep_folders', []) or []
            name_key = 'name' if type == 'folders' else 'names'
            
            for criteria in _rule['detect'][type]:
                criteria_names = criteria[name_key] if type == 'files' else [criteria['name']]
                add = True
                for file_name in criteria_names:
                    if type == 'folders' and file_name in dep_folders:
                        add = False
                    if file_name in exclusions:
                        add = False
                if add:
                    matches_expected_num += 1
            return matches_expected_num

        matches_expected_num += get_matches_expected_num('files')
        matches_expected_num += get_matches_expected_num('folders')

        if state('debug'): print_term('scan:fram', 'D', f'Score threshold for {_rule["name"]}: {matches_expected_num}')

        # Add the rule to the leads array if all of its criteria matched, except if
        # one of its criteria is also in the exclusions
        if _rule['total'] >= matches_expected_num:
            _fw_leads.append(_rule)
            if state('debug'): print_term('scan:fram', 'D', f'Rule {_rule["name"]} added to leads')

    return utils.elect(_fw_leads)


def vanilla_processing(_rules, proj_fld):
    """This function is scanning the project folder to backup and compares its content with the rules
    defined in the vanilla section of the rules file.
    :return: A list containing the "vanilla" rule that matches the most with the project, can return
    several ones if there are multiple rules having the same score ("weight")
    """
    leads = []
    print_term('scan', 'I', 'Running deep scan...')
    if state('debug'): print_term('scan:vani', 'D', f'Starting vanilla processing for project folder: {proj_fld}')
    scored_v_rules = deep_scan(proj_fld, _rules)
    for svr in scored_v_rules:
        if svr['total']:
            leads.append(svr)
            if state('debug'): print_term('scan:vani', 'D', f'Lead found: {svr["name"]} with total: {svr["total"]}')
    # If the weight of the rule that has the heaviest score is lighter than the threshold,
    # We empty the leads list
    # _elected_rule = utils.elect(leads)
    # if not _elected_rule:
    #     leads = list([])
    # else:
    #     leads = list([_elected_rule[0]])
    return leads


def deep_scan(proj_fld, rules):
    """Crawl the project to find files matching the extensions we provide to this function
    :param proj_fld: text, the folder we want to process
    :param rules: object list containing languages names, extensions to crawl and weights
    :return: an updated list with some more weight (hopefully)
    """
    dep_folders = utils.get_dependency_folders(rules['frameworks'] + rules['vanilla'])
    for rule in rules['vanilla']:
        exclusions = rule['actions']['exclude']
        if 'total' not in rule.keys():
            rule['total'] = 0
        for ext_elem in rule['detect']['extensions']:
            for ext in ext_elem['names']:
                if state('debug'): print_term('scan:iglob', 'D', f'Processing extension: {ext} for rule: {rule["name"]}')
                for file_path in glob.iglob(f'{proj_fld}/**/*{ext}', recursive=True):
                    if not excluded(file_path, exclusions, dep_folders):
                        rule['total'] += ext_elem['weight']
                        if state('debug'): print_term('scan:iglob', 'D', f'Matched: {file_path} for rule: {rule["name"]}, updated total: {rule["total"]}')
                    else:
                        if state('debug'): print_term('scan:iglob', 'D', f'Excluded: {file_path} for rule: {rule["name"]}')
        if state('debug'): print_term('scan:iglob', 'D', f'Total for rule {rule["name"]}: {rule["total"]}')
    return rules['vanilla']


def prune_tried_rules(_rules, _tmp_file, history_type):
    """This function is responsible for removing the rules that have already
    been tried from the list of rules that are left to be tested.
    :return: A list of rules that have not been tried yet
    """
    _remaining_rules = _rules[history_type].copy()
    for _rule_name in _tmp_file[history_type]:
        for _rule in _rules[history_type]:
            if _rule['name'] == _rule_name:
                _remaining_rules.remove(_rule)
    return _remaining_rules


def excluded(path, exclusions, dep_folders):
    """Check if a path should be excluded based on exclusions and dependency folders."""
    for exclusion in exclusions:
        if exclusion in path:
            return True
    for dep_folder in dep_folders:
        if dep_folder in path:
            return True
    return False
