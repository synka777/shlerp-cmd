# shlerp-cli
[![](https://img.shields.io/static/v1?label=Status&message=Ongoing&color=green)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.3&color=purple)](#)
___

Normally if you need to provide a copy of the project you're currently working on to one of your colleagues, you would have to remove the dependencies folder first, do the archive using your computer's GUI and then reinstall the dependencies to resume working on your project. Tiresome, right?

***This CLI tool aims to facilitate the backup/duplication/archiving of your development projects.***

- It enables you to make copies/archives of your development project as fast as typing `shlerp`
- It uses [matching rules](./docs/RULESYSTEM.md) that detects the language of the project you're currently working on so that you can specify exclusions.
- Excludes hidden files by default to avoid including .env and IDE-specific files (for example)
- Allows you to choose where you want to do your backup/archive
- Avoids the need to go through the GUI to make copies/archives manually

### Requirements:
- Python 3 (highly recommended)
- Bash or Zsh
  
Note: if you're using a shell other than bash or zsh, you'll have to find a way to make the function in function.template available throughout your whole system.


## 🚀 Quickstart

To install the CLI on your system, open a terminal and make sure you're using bash or zsh:
```
echo "$SHELL"
```
Then you just have to use the setup.py file included in this project:
```
python ./setup.py
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
| Option  |                                                                                                |
| ------------ |------------------------------------------------------------------------------------------------|
| -p, --path PATH  | The path of the project we want to backup.                                                     |
| -o, --output PATH  | The location where we want to store the backup                                                 |
| -r, --rule TEXT  | Manually specify a rule name if you want to skip the language detection process                |
| -d, --dependencies  | Includes the folders marked as dependency folders in the duplication. Only works when using -a |
| -ne, --noexcl  | Disables the exclusion system inherent to each rule                                            |
| -ng, --nogit  | Excludes git data from the backup                                                              |
| -kh, --keephidden  | Excludes hidden files and folders from the backup but keeps git data                           |
| -a, --archive | Archives the project folder instead of making a copy of it                                     |
