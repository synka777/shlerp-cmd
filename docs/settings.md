# shlerp-cmd
[![](https://img.shields.io/static/v1?label=Platform&message=Linux%20%7C%20macOS&color=deeppink)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9%2B&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.7&color=purple)](#)
___

### The settings.json file in detail

So as I'm writting this doc, the full settings file looks like this:
```
{
    "rel_logs_path": ".local/logs",
    "verbose": false,
    "logging": {
        "prune": {
            "enabled": true,
            "max_days": 30
        },
        "no_prune": {
            "max_log_size": 50000
        }
    },
    "rules": {
        "history_limit": {
	        "frameworks": 2,
	        "vanilla": 1
        }
    }
}
```

Let's dive into what these parameters do.

###### 1/ First, we have:

```"rel_logs_path```, which is used by the logging function that is defined in /tools/utils.py. It can be edited 
to specify where you want to store shlerp logs.

##### Note: These paths are relative to the home of the user you are currently using, so please ensure that you choose a location that is still under the home of your current user.

```verbose```, which is disabled by default. Keeping this option disabled will limit the amount of information displayed in the terminal when shlerp is running, setting it to true will have the effect to show the files and folders that are being backed up.

###### 2/ Then, the```"logging"``` section
lists parameters that are related to the logging behavior of shlerp. It is composed of two subsections:

- ```"prune"```, that corresponds to a smart logging management system that will keep only X log entries within a central log file.
- ```"no_prune"```, that corresponds to a "legacy" logging system. It basically creates a new log file each time the maximum log size is reached by the most recent log file.

Please note, the ```"prune"``` mode is the one that is enabled by default by the ```enabled``` parameter. It is so that you don't have to worry about your logs growing too large.

Setting ```"enabled"``` to false will make shlerp us the "legacy" logging mode that is only useful if you want to keep track of your old backup jobs at all times.

###### 3/ The ```"rules"``` section
only contains the ```"history_limit"``` subsection.
It has one setting for each type of rule we want to limit: ```frameworks```, and ```vanilla```.
It sets the maximum number of rules to store into the history file before switching to the whole ruleset at the rule detection step.
Please see the doc related to [matching rules](./rulesystem.md) if you need more details on this topic.

[Back to main README](https://github.com/synka777/shlerp-cmd)