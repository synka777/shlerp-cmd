"""Node save script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the MIT license
"""
import sys
import os
import shutil
import glob
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo


def exists(path):
    """Checks if a file or folder exists
    :param path: String referring to the path we want to check
    :return: A boolean
    """
    return True if os.path.exists(path) else False


def get_files(path):
    """Lists the files contained in a given folder, without symlinks
    :param path: String referring to the path that needs it's content to be listed
    :return: A list of files only, symlinks not included
    """
    return [file for file in os.listdir(path) if not os.path.islink(path + file) and file != 'node_modules']


def get_dt():
    """
    :return: A timestamp in string format
    """
    return str(datetime.now().strftime('%d%m%y%H%M%S'))


def build_archive(project_fld, dst_path):
    with ZipFile(f'{dst_path}.zip', 'w', ZIP_DEFLATED, compresslevel=9) as zip_archive:
        for filename in glob.iglob(project_fld + '/**', recursive=True):
            if 'node_modules' not in filename:
                filename = filename.split(f'{project_fld}/')[1]
                # If the filename is actually a symbolic link, use zip_info and zipfile.writestr()
                # Source: https://gist.github.com/kgn/610907
                if os.path.islink(filename):
                    # http://www.mail-archive.com/python-list@python.org/msg34223.html
                    zip_info = ZipInfo(filename)
                    zip_info.create_system = 3
                    # long type of hex val of '0xA1ED0000L',
                    # say, symlink attr magic...
                    zip_info.external_attr = 2716663808
                    zip_archive.writestr(zip_info, os.readlink(f'./{filename}'))
                else:
                    zip_archive.write(f'./{filename}')


def duplicate(elem_list, path, dst, cache):
    """Duplicates a project folder, processes all files and folders. node_modules will be processed last if cache = True
    :param elem_list, list of strings that represents files and folder to process
    :param path, string that represents the project folder we want to duplicate
    :param dst, string that represents the destination folder where we will be copy the project files
    :param cache, boolean
    """
    try:
        os.mkdir(dst)
        for elem in elem_list:
            orig = f'{path}/{elem}'
            full_dst = f'{dst}/{elem}'
            if os.path.isdir(orig):
                shutil.copytree(orig, full_dst, symlinks=True)
                if exists(full_dst):
                    print(f'Done: {full_dst}/')
            else:
                shutil.copy(orig, full_dst)
                if exists(full_dst):
                    print(f'Done: {full_dst}')

        print('OK - Project duplicated')
        if cache:
            print('Processing node_modules...')
            shutil.copytree(f'{path}/node_modules', f'{dst}/node_modules', symlinks=True)
            print(f'Done: {dst}/node_modules/')

    except Exception as exc:
        print('Copy: Error during the duplication', exc)


def main(path, auto_inst, cache, archive):
    package_file = exists(f'{path}/package.json')

    # 1. Check if the current folder is a javascript project
    if package_file:
        print('OK - package.json found')
        elements = get_files(path)
        node_modules = exists(f'{path}/node_modules')
        dst = f'{path}_{get_dt()}'

        if archive:
            # If the -a switch is provided to the script, we use build_archive() and exclude the node_module folder
            build_archive(path, dst)
        else:
            # Else if we don't want an archive we will do a copy of the project instead
            if not cache:
                # Copy everything except the node_modules folder
                duplicate(elements, path, dst, False)
                if auto_inst:
                    print('Installing npm packages...')
                    os.system('npm i')
            else:
                if node_modules:
                    duplicate(elements, path, dst, True)
                else:
                    duplicate(elements, path, dst, False)
    else:
        print(f'{path} is not a node project')
        exit()


if __name__ == '__main__':
    auto_install = use_cache = is_archive = False
    folder = ''
    for index, arg in enumerate(sys.argv):
        if arg == '--cache' or arg == '-c':
            use_cache = True
        if arg == '--autoinstall' or arg == '-ai':
            auto_install = True
        if arg == '--path' or arg == '-p':
            try:
                folder = sys.argv[index+1]
            except Exception as e:
                print('Please provide a path to a evaluate for -p: ', e)
        if arg == '--archive' or arg == '-a':
            is_archive = True
    main(folder, auto_install, use_cache, is_archive)
