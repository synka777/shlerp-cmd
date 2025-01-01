<div align="center">
  <img src="resources/rocket_shlerp.png" alt="shlerp logo" width="250">
</div>

# shlerp-cmd
[![](https://img.shields.io/static/v1?label=Platform&message=Linux%20%7C%20macOS&color=deeppink)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9%2B&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.7&color=purple)](#)
___

Normally if you need to provide a copy of the project you're currently working on to one of your colleagues, you would have to remove the dependencies folder first, do the archive using your computer's GUI and then reinstall the dependencies to resume working on your project. Tiresome, right?

***This CLI tool aims to facilitate the backup/duplication/archiving of your development projects.***

- It enables you to make copies/archives of your development project as fast as typing `shlerp`
- It uses [matching rules](./docs/rulesystem.md) that detects the language of the project you're currently working on so that you can specify exclusions.
- Excludes hidden files by default to avoid including .env and IDE-specific files (for example)
- Allows you to choose where you want to do your backup/archive
- Avoids the need to go through the GUI to make copies/archives manually

### Requirements:
- Python 3 (highly recommended)
- Bash or Zsh (Windows shells & file system are not supported)
  
Note: if you're using another UNIX/Linux shell than bash or zsh, you'll have to find a way to make the function in alias.sh available throughout your whole system.


## 🚀 Quickstart

To install the CLI on your system, open a terminal and make sure you're using bash or zsh:
```
echo "$SHELL"
```
Position yourself into the folder you want to install shlerp into, and then run:
```
git clone https://github.com/synka777/shlerp-cmd.git && cd shlerp-cmd && python3 setup.py
```
After this, restart your terminal and you're all set!


## 🗄 Example use cases

- If you need to make a quick duplicate of your node.js working directory, just do:
```
shlerp
```
It will make a copy of your project without the node_modules folder

- If you need to send a copy of your code to your students and you don't want to include your nasty git history, just do:
```
shlerp -ng / shlerp --nogit
```

- Or, if you need to archive it:
```
shlerp -ng -a / shlerp --nogit --archive
```


## 🛠 Full option list
| Option             |                                                                                                                                                                                     |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| -t, --target PATH    | The path of the project we want to backup.  If not provided the current working directory will be backed up                                                                                                                                          |
| -o, --output PATH  | The location where we want to store the backup                                                                                                                                      |
| -a, --archive      | Archives the project folder instead of making a copy of it                                                                                                                          |
| -u, --upload      | Make an archive (Max: 2GB), upload it to file.io and get the download url. Can be used as is, but a customized validity period can be set following this pattern: ^[1-9]d*[y|Q|M|w|d|h|m|s]$                                                                                                                        |
| -r, --rule TEXT    | Manually specify a rule name if you want to skip the language detection process                                                                                                     |
| -b, --batch        | This option will consider all the sub-folders from the cwd as repositories and process it one by one. This is especially useful to backup all your projects on an another location. |
| -d, --dependencies | Include the folders marked as dependency folders in the duplication. Only works when using -a                                                                                      |
| -ne, --noexcl      | Disable the exclusion system inherent to each rule                                                                                                                                 |
| -ng, --nogit       | Exclude git data from the backup                                                                                                                                                   |
| -kh, --keephidden  | Include hidden files and folders in the backup (they are excluded by default, except for git-related ones)                                                                                                               |
| -hl, --headless  | Run in headless mode; without displaying anything in the terminal                                                                                                               |
| -h, --help  | Shows this help menu with all the options that can be used                                                                                                                |