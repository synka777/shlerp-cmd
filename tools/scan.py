###############################################################
# This file features the main functions that are used by the 
# rule detection system to scan the project and find out the
# language/framework context that is used in a particular project

from tools.piputils import print_term
import tools.utils as utils
from os.path import exists

def frameworks_processing(_rules, proj_fld):
    """This function is responsible for scanning the project and comparing it
    with the rules defined in the frameworks defines in the rules file.
    :return _fw_leads: A list of rules of type framework that have been matched with the project,
    will usually return only one result but can return multiple if they have the same score ("weight")
    """
    _fw_leads = [] # fw_leads stands for frameworks_leads
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
    return utils.elect(_fw_leads)


def vanilla_processing(_rules, threshold, proj_fld, uid):
    """This function is scanning the project folder to backup and compares its content with the rules
    defined in the vanilla section of the rules file.
    :return: A list containing the "vanilla" rule that matches the most with the project, can return
    several ones if there are multiple rules having the same score ("weight")
    """
    print_term('scan', 'I', 'Crawling...', uid)
    leads = utils.crawl_for_weight(proj_fld, _rules['vanilla'])
    # If the weight of the rule that has the heaviest score is lighter than the threshold,
    # We empty the leads list
    _elected_rule = utils.elect(leads)
    if not _elected_rule:
        leads = list([])
    else:
        leads = list([]) if _elected_rule[0]['total'] < threshold else list([_elected_rule[0]])
    return leads


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