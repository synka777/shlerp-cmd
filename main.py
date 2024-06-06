"""Backup script
Copyright (c) 2023 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the GNU Affero General Public License v3.0
"""
import utils
import os
import shutil
import glob
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import time
import click
from click import echo
import json


def auto_detect():

    return None


def build_archive(project_fld, dst_path, uid, started):
    """Makes an archive of a given folder, without node_modules
    :param project_fld: text, the folder we want to archive
    :param dst_path: text, the location where we want to store the archive
    :param uid: text representing a short uid
    :param started: number representing the time when the script has been executed
    """
    with ZipFile(f'{dst_path}.zip', 'w', ZIP_DEFLATED, compresslevel=9) as zip_archive:
        fld_count = file_count = symlink_count = 0
        success = False
        for filename in glob.iglob(project_fld + '/**', recursive=True):
            if 'node_modules' not in filename:
                rel_filename = filename.split(f'{project_fld}/')[1]
                # Exclude '' (listed by iglob when the script is executed from another path in a terminal)
                if rel_filename != '':
                    # If the filename is actually a symbolic link, use zip_info and zipfile.writestr()
                    # Source: https://gist.github.com/kgn/610907
                    if os.path.islink(filename):
                        symlink_count += 1
                        # http://www.mail-archive.com/python-list@python.org/msg34223.html
                        zip_info = ZipInfo(filename)
                        zip_info.create_system = 3
                        # long type of hex val of '0xA1ED0000L',
                        # say, symlink attr magic...
                        zip_info.external_attr = 2716663808
                        try:
                            zip_archive.writestr(zip_info, os.readlink(f'{filename}'))
                            echo(f'[{uid}:{utils.get_dt()}:arch] Done: {rel_filename}')
                            success = True
                        except Exception as exc:
                            echo(f'[{uid}:{utils.get_dt()}:arch]'
                                 f'A problem happened while handling {rel_filename}: {exc}')

                    else:
                        try:
                            zip_archive.write(f'{filename}', arcname=f'{rel_filename}')
                            if os.path.isdir(filename):
                                fld_count += 1
                            else:
                                file_count += 1
                            echo(f'[{uid}:{utils.get_dt()}:arch] Done: {rel_filename}')
                            success = True
                        except Exception as exc:
                            echo(
                                f'[{uid}:{utils.get_dt()}:arch] '
                                f'A problem happened while handling {rel_filename}: {exc}')
        if success:
            echo('------------')
            echo(f'[{uid}:{utils.get_dt()}:arch] '
                 f'Folders: {fld_count} - '
                 f'Files: {file_count} - '
                 f'Symbolic links: {symlink_count}')
            echo(
                f'[{uid}:{utils.get_dt()}:arch] '
                f'✅ Project archived ({"%.2f" % (time.time() - started)}s): {dst_path}.zip')
        else:
            echo(f'[{uid}:{utils.get_dt()}:arch] Warning - Corrupted archive: {dst_path}.zip')


def duplicate(path, dst, cache, uid, started):
    """Duplicates a project folder, processes all files and folders. node_modules will be processed last if cache = True
    :param path, string that represents the project folder we want to duplicate
    :param dst, string that represents the destination folder where we will copy the project files
    :param cache, boolean
    :param uid, text representing a short uid
    :param started: number representing the time when the script has been executed
    """
    try:
        fld_count = file_count = symlink_count = 0
        elem_list = utils.get_files(path)
        os.mkdir(dst)
        for elem in elem_list:
            orig = f'{path}/{elem}'
            full_dst = f'{dst}/{elem}'
            if os.path.isdir(orig):
                shutil.copytree(orig, full_dst, symlinks=True)
                if utils.exists(full_dst):
                    echo(f'[{uid}:{utils.get_dt()}:copy] Done: {path}/{elem}')
                    fld_count += 1
            else:
                shutil.copy(orig, full_dst)
                if os.path.islink(elem):
                    symlink_count += 1
                else:
                    file_count += 1
                if utils.exists(full_dst):
                    echo(f'[{uid}:{utils.get_dt()}:copy] Done: {path}/{elem}')
        echo('------------')
        # echo(f'[{uid}:{utils.get_dt()}:arch] '
        #       f'Folders: {fld_count} - '
        #       f'Files: {file_count} - '
        #       f'Symbolic links: {symlink_count}')
        echo(f'[{uid}:{utils.get_dt()}:copy] ✅ Project duplicated ({"%.2f" % (time.time() - started)}s): {dst}/')
        if cache:
            start_cache = time.time()
            echo(f'[{uid}:{utils.get_dt()}:copy] Processing node_modules...')
            shutil.copytree(f'{path}/node_modules', f'{dst}/node_modules', symlinks=True)
            echo(f'[{uid}:{utils.get_dt()}:copy] Done ({"%.2f" % (time.time() - start_cache)}s): {dst}/node_modules/')
    except Exception as exc:
        echo(f'[{uid}:{utils.get_dt()}:copy] Error during the duplication', exc)


@click.command()
@click.option('-p', '--path', type=click.Path(),
              help='The path of the project we want to backup. Please use absolute paths for now')
@click.option('-o', '--output', type=click.Path(),
              help='The location where we want to store the backup')
@click.option('-c', '--cache', default=False,
              help='Includes node_modules in the duplication. Only works in conjunction with -a',
              is_flag=True)
@click.option('-ai', '--autoinstall', default=False,
              help='Installs the node modules. Don\'t use it with -c.',
              is_flag=True)
@click.option('-a', '--archive', default=False,
              help='Archives the project folder instead of making a copy of it',
              is_flag=True)
def main(path, output, cache, autoinstall, archive):
    """Dev projects backups made easy"""
    start_time = time.time()
    if path:
        proj_fld = os.path.abspath(path)
    else:
        proj_fld = os.getcwd()

    # Check if the current folder is a javascript project
    if utils.exists(f'{proj_fld}/package.json'):
        uid = utils.suid()
        echo(f'[{uid}:{utils.get_dt()}] Package.json found')
        node_modules = utils.exists(f'{proj_fld}/node_modules')
        # If we don't have a particular output folder, use the same as the project
        if output:
            output = os.path.abspath(output)
            project_name = proj_fld.split('/')[-1]
            dst = f'{output}/{project_name}_{utils.get_dt()}'
        else:
            dst = f'{proj_fld}_{utils.get_dt()}'
        if archive:
            # If the -a switch is provided to the script, we use build_archive() and exclude the node_module folder
            build_archive(proj_fld, dst, uid, start_time)
        else:
            # Else if we don't want an archive we will do a copy of the project instead
            if not cache:
                # Copy everything except the node_modules folder
                duplicate(proj_fld, dst, False, uid, start_time)
                if autoinstall:
                    echo('Installing npm packages...')
                    os.system('npm i')
            else:
                if autoinstall:
                    echo(f'[{uid}:{utils.get_dt()}] Info: -ai/--autoinstall discarded by -c/--cache')
                if node_modules:
                    duplicate(proj_fld, dst, True, uid, start_time)
                else:
                    duplicate(proj_fld, dst, False, uid, start_time)
    else:
        echo(f'{proj_fld} is not a node project')
        exit()


if __name__ == '__main__':
    main()
