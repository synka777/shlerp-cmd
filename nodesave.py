"""Node save script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the MIT license
"""
import sys
import os
import shutil


def exists(path):
    """Checks if a file or folder exists
    :param path: String referring to the path we want to check
    :return:
    """

    #print(get_files('.'))
    return True if os.path.exists(path) else False


def get_files(path):
    """Lists the files contained in a given folder, without symlinks
    :param path: String referring to the path that needs it's content to be listed
    :return: A list of files only, symlinks not included
    """
    return [file for file in os.listdir(path) if not os.path.islink(path + file)]


def backup_node_modules(path):
    """
    This option will be useful if we want to use the cache option, to avoid downloading the npm packages again.
    :return:
    """
    #TODO: check if the node_modules folder is already in the backup folder, if it already in it remove the old one
    #TODO: backup the node_modules folder with project name and date in the folder name
    try:
        shutil.copy(path, '~/bkp/node_modules')
        if os.path.exists('~/bkp/node_modules'):
            print('Successfully backed up node_modules folder')
    except Exception as e:
        print('Copy: Error when parsing node_modules folder ', e)
    return ''


def restore_node_modules():
    """

    :return:
    """
    return ''


def is_backed_up():
    """

    :return:
    """
    return ''


def get_file_name():
    """

    :return:
    """
    return ''


def main(path, auto_inst, cache):
    package_file = exists(f'{path}/package.json')
    #
    # 1. Check if the current folder is a javascript project
    #
    if package_file:
        print('package.json found')
        #
        # 2. If so, backup node_modules folder
        #
        if cache:
            node_modules = exists(f'{path}/node_modules')
            if node_modules:
                backup_node_modules()
            else:
                print('No node_modules found, will now proceed to copy')
        #
        # When the node_modules is backed up
        #
        is_backed_up()

        #
        # Duplicate the folder with the current date and timestamp
        #
        get_file_name()

        #
        # Automatically do npm i if we choose to do so with a command-line parameter.
        #
        if auto_inst:
            print('npm i')
    else:
        print(f'{path} is not a node project')
        exit()


if __name__ == '__main__':
    auto_install = False
    folder = ''
    use_cache = False
    for index, arg in enumerate(sys.argv):
        if arg == '--cache' or arg == '-c':
            use_cache = True
        if arg == '--autoinstall' or '-ai':
            auto_install = True
        if arg == '--path' or arg == '-p':
            try:
                folder = sys.argv[index+1]
            except Exception as e:
                print('Please provide a path to a evaluate for -p: ', e)
    main(folder, auto_install, use_cache)
