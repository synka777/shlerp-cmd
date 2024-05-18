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
    :return: A list of files, without any possible node_modules folder
    """
    return [file for file in os.listdir(path) if file != 'node_modules']


def rectify(path):
    """rectifies the path, removes typos like double slashes and possible trailing slashes if there is one
    :param path: String that corresponds to a folder to use in the script
    :return: A string corresponding to the rectified path
    """
    while '//' in path:
        path = path.replace('//', '/')
    return [path[:-1] if path.endswith('/') else path][0]


def get_dt():
    """
    :return: A timestamp in string format
    """
    return str(datetime.now().strftime('%d%m%y%H%M%S'))


def build_archive(project_fld, dst_path):
    with ZipFile(f'{dst_path}.zip', 'w', ZIP_DEFLATED, compresslevel=9) as zip_archive:
        success = False
        for filename in glob.iglob(project_fld + '/**', recursive=True):
            if 'node_modules' not in filename:
                rel_filename = filename.split(f'{project_fld}/')[1]
                # Exclude '' (listed by iglob when the script is executed from another path in a terminal)
                if rel_filename != '':
                    # If the filename is actually a symbolic link, use zip_info and zipfile.writestr()
                    # Source: https://gist.github.com/kgn/610907
                    if os.path.islink(filename):
                        # http://www.mail-archive.com/python-list@python.org/msg34223.html
                        zip_info = ZipInfo(filename)
                        zip_info.create_system = 3
                        # long type of hex val of '0xA1ED0000L',
                        # say, symlink attr magic...
                        zip_info.external_attr = 2716663808
                        try:
                            zip_archive.writestr(zip_info, os.readlink(f'{filename}'))
                            print(f'[{get_dt()}::archive] Done: {rel_filename}')
                            success = True
                        except Exception as exc:
                            print(f'[{get_dt()}::archive] A problem happened while handling {rel_filename}: {exc}')

                    else:
                        try:
                            zip_archive.write(f'{filename}', arcname=f'{rel_filename}')
                            print(f'[{get_dt()}::archive] Done: {rel_filename}')
                            success = True
                        except Exception as exc:
                            print(f'[{get_dt()}::archive] A problem happened while handling {rel_filename}: {exc}')
        if success:
            print(f'[{get_dt()}::archive] ✅ Project archived: {dst_path}.zip')
        else:
            print(f'[{get_dt()}::archive] Warning - Corrupted archive: {dst_path}.zip')


def duplicate(path, dst, cache):
    """Duplicates a project folder, processes all files and folders. node_modules will be processed last if cache = True
    :param path, string that represents the project folder we want to duplicate
    :param dst, string that represents the destination folder where we will copy the project files
    :param cache, boolean
    """
    try:
        elem_list = get_files(path)
        os.mkdir(dst)
        for elem in elem_list:
            orig = f'{path}/{elem}'
            full_dst = f'{dst}/{elem}'
            if os.path.isdir(orig):
                shutil.copytree(orig, full_dst, symlinks=True)
                if exists(full_dst):
                    print(f'[{get_dt()}::copy] Done: {path}/{elem}')
            else:
                shutil.copy(orig, full_dst)
                if exists(full_dst):
                    print(f'[{get_dt()}::copy] Done: {path}/{elem}')

        print(f'[{get_dt()}] ✅ Project duplicated in: {dst}/')
        if cache:
            print(f'[{get_dt()}::copy] Processing node_modules...')
            shutil.copytree(f'{path}/node_modules', f'{dst}/node_modules', symlinks=True)
            print(f'[{get_dt()}::copy] Done: {dst}/node_modules/')

    except Exception as exc:
        print('Copy: Error during the duplication', exc)


def main(path, output_fld, auto_inst, cache, archive):
    package_file = exists(f'{path}/package.json')
    # 1. Check if the current folder is a javascript project
    if package_file:
        print(f'[{get_dt()}] Package.json found')
        node_modules = exists(f'{path}/node_modules')
        # If we don't have a particular output folder, use the same as the project
        if output_fld != '':
            project_name = path.split('/')[-1]
            dst = f'{output_fld}/{project_name}_{get_dt()}'
        else:
            dst = f'{path}_{get_dt()}'
        if archive:
            # If the -a switch is provided to the script, we use build_archive() and exclude the node_module folder
            build_archive(path, dst)
        else:
            # Else if we don't want an archive we will do a copy of the project instead
            if not cache:
                # Copy everything except the node_modules folder
                duplicate(path, dst, False)
                if auto_inst:
                    print('Installing npm packages...')
                    os.system('npm i')
            else:
                if node_modules:
                    duplicate(path, dst, True)
                else:
                    duplicate(path, dst, False)
    else:
        print(f'{path} is not a node project')
        exit()


if __name__ == '__main__':
    auto_install = use_cache = is_archive = False
    proj_fld = ''
    output = ''
    for index, arg in enumerate(sys.argv):
        if arg == '--cache' or arg == '-c':
            use_cache = True
        if arg == '--autoinstall' or arg == '-ai':
            auto_install = True
        if arg == '--path' or arg == '-p':
            try:
                proj_fld = rectify(sys.argv[index + 1])
            except Exception as e:
                print('Please provide a path to a evaluate for -p: ', e)
        if arg == '--output' or arg == '-o':
            try:
                output = rectify(sys.argv[index + 1])
            except Exception as e:
                print('Please provide a path to a evaluate for -o: ', e)
        if arg == '--archive' or arg == '-a':
            is_archive = True
    main(proj_fld, output, auto_install, use_cache, is_archive)
