# shlerp-cmd
[![](https://img.shields.io/static/v1?label=Platform&message=Linux%20%7C%20macOS&color=deeppink)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9%2B&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.7&color=purple)](#)
___

### The language/framework auto-detection system in detail

1. [What does this system do](#1-what-does-this-detection-system-do)
2. [Components used by this system](#2-components-used-by-this-system)
3. [How the system uses these components](#3-how-shlerp-uses-these-components)
4. [How shlerp uses this system](#4-how-shlerp-uses-this-system)

### 1. What does this detection system do

The shlerp script contains a rules.json file, with a predefined array of matching rules.
These rules are here to determine which language or framework is used for the current project.

Once the system has guessed which language is used, it will then go through the actions defined into the action section of the detected rule.
At the time the only action that has been implemented is folder and file exclusions.

So for example; for a rule that describes Javascript or Node.js projects, we will search for javascript/Node.js files with the language detection and then, we will exclude the node_modules folder from the backup.

This is how shlerp saves you time.

### 2. Components used by this system

The rulesystem works with two rule systems.
#### Framework rules:
A full framework rule looks like this. When this type of matching rule is evaluated by shlerp, shlerp will verify the matching criteria that are defined into the "detect" section of the rule.
The rule that have all of its criteria matched will be elected as the rule to be used when the backup will be done.
Multiple frameworks can be detected at once.
```json
{
    "name":"React_native",
    "detect":{
        "files":[
            {
                "names":["package.json", "package-lock.json"],
                "pattern":"react-native",
                "weight":6
            }
        ],
        "folders":[
            {
                "name":".expo-shared",
                "files":["assets.json"],
                "weight":6
            },
            {
                "name":"node_modules",
                "files":[],
                "weight":2
            }
        ]
    },
    "actions":{
        "exclude":{
            "files":["test-excl.txt"],
            "folders":[],
            "dep_folder": "node_modules"
        }
    }
}
```
Notes on the ```files``` subsection:

When you see multiple files declared into the "names" array of a file criteria, it means that the criteria will match if one of these file names is found into the project you want to process.

When "pattern" is defined, the weight will only be added to the rule score if a certain string pattern is found within the file we are searching for.

Note on the ```folders``` subsection: The "files" subsection of "folders" is there if you make sure that certain files exist within the given folder before considering that the criteria is matched.


#### Vanilla rules:
This type of rule lists file extensions. When shlerp evaluates these rules, each time a file of a given extension is found, a score "weight" is added to the rule.
A full Vanilla looks like this. The "detect" section lists file extensions with a weight (score).
Each time a file of a given extension that's declared here is found into the project we want to backup, we add it to the detected rules.
```json
{
    "name":"Python",
    "detect":{
        "extensions":[
            {
                "names":["*.py"],
                "weight":0.5
            }
        ]
    },
    "actions":{
        "exclude":{
            "files":[],
            "folders":["venv", "__pycache__"],
            "dep_folder": null
        }
    }
}
```

### 3. How shlerp uses these components?

So the workflow shlerp follows is like the following:
```
BEGIN
Framework rules processing:
- Scan the files and folders by checking the existence of files, folders and text patterns in files
	- Each framework rule that has all its criteria matched is added to the list of rules to use with the backup
- Run a deep scan to make sure we detect all other possible languages, by searching for file extensions:
	- Each file extension that is found will make its parent rule part of the rule set that'll be applied when backing up.
END
```
Why is it designed like this? To make sure the detection system does not miss anything. In earlier versions there was a history system that privileged the X last frameworks and languages that were detected, but it became obsolete as soon as the capability to detect multiple languages and folders got added to the shlerp project.

### 4. How shlerp uses this system

Once we know which rules are the ones that matches the best the technologies of the project we currently want to process, the script will apply the actions that are defined into the elected rules. It will only support files and folders exclusions as I'm writing this.
```json
"actions":{
     "exclude":{
         "files":["test-excl.txt"],
         "folders":[],
         "dep_folder": "node_modules"
     }
}
```
 - "files" is the list of files we want to exclude from the backup, and "folders" just follows the same principle.
 - "dep_folder" is a special type of folders where are stored your project dependencies. 
 When you duplicate a project, in some cases like javascript the data that takes the most time to copy is the well-known "node_modules" dependencies folder, which can grow quite large most of the time.


... and that's it. New detection rules can be added into the rules.json file, you can create new ones for any language or framework you want.

[Back to main README](https://github.com/synka777/shlerp-cmd)