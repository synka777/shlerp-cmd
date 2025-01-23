<div align="center">
  <img src="assets/rocket_shlerp.png" alt="shlerp logo" width="250">
</div>

# shlerp-cmd

[![](https://img.shields.io/static/v1?label=Platform&message=Linux%20%7C%20macOS&color=deeppink)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9%2B&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.7&color=purple)](#)

---

Effortlessly manage, back up, and share your development projects without breaking a sweat! Shlerp eliminates the repetitive and error-prone steps involved in creating clean archives of your work, offering a fast and efficient alternative to traditional GUI methods or manual scripting.

## 🚀 What is Shlerp?

Whether you're collaborating on code, archiving your progress, or sharing projects with others, Shlerp makes it as easy as typing a single command.

Key Benefits:

- Instant Archiving: Create project backups or archives by typing shlerp in your terminal.
- Language Detection: Automatically detects the project's languages/frameworks and applies tailored exclusion rules.
- Customizable Rules: Define your own file-matching rules to suit unique project needs.
- Cleaner Backups: Excludes unnecessary or sensitive files (e.g., .env, IDE-specific files) by default while keeping Git-related ones.
- Flexible Destinations: Easily specify where your archives or backups should go.
- Fast Sharing: Generate single-use download links for projects under 2GB—ideal for remote collaboration.
- Git-Like Simplicity: A perfect alternative when Git feels too heavy-handed for small, quick, or ad-hoc project transfers.

Supported by default:
Frameworks: Ionic (Cordova/Capacitor), React Native, Flask, Spring boot Laravel
Programming languages: Python, Javascript, Java, Rust, PHP

## ⚙️ Requirements:

- Python 3 (highly recommended)
- Bash or Zsh (Windows shells & file system are not supported)

Note: if you're using another UNIX/Linux shell than bash or zsh, you'll have to find a way to make the function in alias.sh available throughout your whole system.

## 🚀 Quick Installation

1. To install the CLI on your system, open a terminal and make sure you're using bash or zsh:

   ```
   echo "$SHELL"
   ```
2. Clone the repository and install Shlerp:

   ```
   git clone https://github.com/synka777/shlerp-cmd.git && cd shlerp-cmd && python3 setup.py
   ```
3. Restart your terminal, and you're ready to go!

## 🗄 Use cases

Shlerp simplifies common workflows:

1. Clean Project Duplicates

Want to create a quick copy of your Node.js project without the bulk of `node_modules`?

```
shlerp
```
![](https://i.imgur.com/zzoYZe9.gif)

2. Share Projects Without Git History

Need to send your students a clean version of your code? Exclude the Git history in seconds:

```
shlerp -a -ng
```
![](https://i.imgur.com/t0Zr4oB.gif)

3. Generate a Quick Share Link

Send your latest code updates to a collaborator via a single-use download link:

```
shlerp -u
```
![](https://i.imgur.com/n6fsXcm.gif)

4. Automated Backups

Back up your active development folders to an external drive using a simple command (great for `cron` jobs):

```
shlerp -b -o /dev/disk1s1
```
![](https://i.imgur.com/ou52mIP.gif)

## 🌟 Why Use Shlerp?

Unlike Git or GitHub, Shlerp is designed for simplicity and speed when:

- You need a quick local copy or archive without version control overhead.
- Sharing a temporary project snapshot is faster than pushing to a remote repository.
- Automating backups is more relevant than detailed commit history.

For developers who juggle multiple tools and workflows, Shlerp ensures your files are ready to share, archive, or backup without the hassle.

Start simplifying your development life today—just `shlerp` it!


## 📄 More docs

- [Rule system details](./docs/rulesystem.md)
- [Settings file syntax](./docs/settings.md)

## 🛠 Full option list


| Option             | Description                                                                                                                                                                           |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| -t, --target PATH  | The path of the project we want to backup.  If not provided the current working directory will be backed up                                                                           |
| -o, --output PATH  | The location where we want to store the backup                                                                                                                                        |
| -a, --archive      | Archives the project folder instead of making a copy of it                                                                                                                            |
| -u, --upload       | Make an archive (Max: 2GB), upload it, get the download url. Can be used as is, but a customized validity period can be set following this pattern: ^[1-9]d*[y\|Q\|M\|w\|d\|h\|m\|s]$ |
| -r, --rule TEXT    | Manually specify a rule name if you want to skip the language detection process                                                                                                       |
| -b, --batch        | This option will consider all the sub-folders from the cwd as repositories and process it one by one. This is especially useful to backup all your projects on an another location.   |
| -d, --dependencies | Include the folders marked as dependency folders in the duplication. Only works when using -a                                                                                         |
| -ne, --noexcl      | Disable the exclusion system inherent to each rule                                                                                                                                    |
| -ng, --nogit       | Exclude git data from the backup                                                                                                                                                      |
| -kh, --keephidden  | Include hidden files and folders in the backup (they are excluded by default, except for git-related ones)                                                                            |
| -hl, --headless    | Run in headless mode; without displaying anything in the terminal                                                                                                                     |
| -h, --help         | Shows this help menu with all the options that can be used                                                                                                                            |
