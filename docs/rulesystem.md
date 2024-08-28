# shlerp-cli
[![](https://img.shields.io/static/v1?label=Status&message=Ongoing&color=green)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.3&color=purple)](#)
___


### What does the language detection system do

The shlerp script contains a rules.json file, with a predefined array of matching rules.
These rules are here to determine which language or context is used for the current project.

Once the system has guessed which language is used, it will then go through the actions defined into the action section of the detected rule.
At the time the only action that has been implemented is folder and file exclusions.

So for example; for a rule that describes Javascript or Node.js projects, we will search for javascript/Node.js files with the language detection and then, we will exclude the node_modules folder from the backup.

This is why the shlerp script can make you save time.

#### How it works

So this system works in two steps:
1. Verify if given files and folders exists. It will check full paths at once so it is fast and reliable. When the script is ran for the first time, it will try to use the whole ruleset to determine which language is used for the current project we want to process, until the history of detected languages is filled.
Once the language history is filled, the next time the script is ran it will go through the history first, and only then it will go through the less-used rules to try and search for more rules to match in case if the rules from the history didn't match anything.
Why is it designed like this? Because of runtime issues. The runtime is greatly enhanced if you don't have to go through the ruleset each and every time you run the script, especially if your ruleset is quite large.
Each time a file or folder is matched, a score (weight) is added to the rule.
So each time the script runs, the script searches for weight with each criteria that is defined in every rule.

2. Once we know which rule is the one that matches the best the language of the project we currently want to process, the script will apply the actions that are defined into the elected rule. It will only support files and folders exclusions as I'm writing this.


A full matching rule looks like this:
```javascript
{
        "name":"Javascript",
        "detect":{
            "files":[
                {
                    "name":["tslint.json", "eslint.json", "package.json", "tsconfig.json"],
                    "pattern":null,
                    "weight":4
                },
                {
                    "name":["*.js", "*.ts", "*.jsx"],
                    "pattern":null,
                    "weight":0.5
                }
            ],
            "folders":[
                {
                    "name":"node_modules",
                    "files":[],
                    "weight":2
                }
            ]
        },
        "actions":{
            "exclude":{
                "files":["out.log", "karma.conf.js"],
                "folders":["buildprep", "HEMPTYDIR"],
                "dep_folder": "node_modules"
            }
        }
    }
```
As you can see, it is composed of two main sections:
1. A detection section "detect", that is there to define which elements we want to find.
This section is by itself composed by two subsections: files, and folders.
    - "files": this array is where you can put file objects that will be used
    ```javascript
    {
        "name":["tslint.json", "eslint.json", "package.json", "tsconfig.json"],
        "pattern":null,
        "weight":4
    }
    ```
    Note 1: When file objects are declared without a file name, they will be used in the second step
    Note 2: When "pattern" is defined, the weight will only be added to the rule score if a certain string pattern is found within the file we are searching for.
    
    Another example of file object, with the wildcard " * ":
    ```
    {
        "name":["*.js", "*.ts", "*.jsx"],
        "pattern":null,
        "weight":0.5
    }
    ```
    Note: The files that are declared as an extension, without a file name will only be processed when no weight has been found during the first stage of the detection.
    So, if all rules from the history or from the whole ruleset have been evaluated and no weight has been found at all, shlerp will go through the project another time and try to find some files that match the extensions declared in all rules.
    - "folders": each folder object has a weight.
    ```
    {
        "name":"node_modules",
        "files":[],
        "weight":2
    }
    ```
    Note: The "files" subsection of "folders" is there if you make sure that certain files exist within the given folder before adding weight to the score of the rule that is being evaluated.
    
2. An "action" section. This section lists the actions that will be performed by shlerp when it knows which rule it needs to apply for the current project we want to process.
In this section you will find an "exclude" subsection.
```
"exclude":{
    "files":[],
    "folders":[],
    "dep_folder": "node_modules"
}
```
    - "files" is the list of files we want to exclude from the backup, and "folders" just follows the same principle.
    - "dep_folder" is a special type of folders where are stored your project dependencies. 
    When you duplicate a project, in some cases like javascript the data that takes the most time to copy is the well-known "node_modules" dependencies folder, which can grow quite large most of the time.

... and that's it. New detection rules can be added into the rules.json file, you can create new ones for any language or framework you want, but keep in mind that the lesser matching criterias you put in your rule, the quicker your rule will be evaluated by shlerp and the quicker the language detection will be done.

[Back to main README](https://github.com/synchronic777/shlerp-cli)