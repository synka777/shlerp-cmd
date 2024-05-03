"""Node save script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the MIT license
"""
import sys
import os
import shutil
from datetime import datetime


def exists(path):
    """Checks if a file or folder exists
    :param path: String referring to the path we want to check
    :return:
    """
    return True if os.path.exists(path) else False


def get_files(path):
    """Lists the files contained in a given folder, without symlinks
    :param path: String referring to the path that needs it's content to be listed
    :return: A list of files only, symlinks not included
    """
    return [file for file in os.listdir(path) if not os.path.islink(path + file)]


def get_dt():
    """
    This option will be useful if we want to use the cache option, to avoid downloading the npm packages again.
    :return:
    """
    return str(datetime.now().strftime('%d%m%Y%H%M%S'))


def duplicate(path, dst, cache):
    """Duplicates a project folder, processes all files and folders. node_modules will be processed last if cache = True
    :param path, string that represents the project folder we want to duplicate
    :param dst, string that represents the destination folder where we will be copy the project files
    :param cache, boolean
    """
    element_list = get_files(path)
    try:
        os.mkdir(dst)
        for elem in element_list:
            orig = f'{path}/{elem}'
            full_dst = f'{dst}/{elem}'
            if os.path.isdir(orig):
                if elem != 'node_modules':
                    shutil.copytree(orig, full_dst, symlinks=True)
                    if exists(full_dst):
                        print(f'Done: {full_dst}/')
            else:
                shutil.copy(orig, full_dst)
                if exists(full_dst):
                    print(f'Done: {full_dst}')

        print('Project duplicated', end='')
        if cache:
            print(', processing node_modules...')
            shutil.copytree(f'{path}/node_modules', f'{dst}/node_modules', symlinks=True)
            print(f'Done: {dst}/node_modules/')

    except Exception as exc:
        print('Copy: Error during the duplication', exc)


def main(path, auto_inst, cache):
    package_file = exists(f'{path}/package.json')

    # 1. Check if the current folder is a javascript project
    if package_file:
        print('package.json found')

        node_modules = exists(f'{path}/node_modules')
        dst = f'{path}_{get_dt()}'

        if not cache:
            # Copy everything except the node_modules folder
            duplicate(path, dst, False)
        else:
            if node_modules:
                duplicate(path, dst, True)
            else:
                duplicate(path, dst, False)

        # TODO: Automatically do npm i if we choose to do so with a command-line parameter.
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
