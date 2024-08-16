# shlerp-cli
[![](https://img.shields.io/static/v1?label=Status&message=Ongoing&color=green)](#) [![](https://img.shields.io/static/v1?label=Python&message=v3.9&color=blue)](#) [![](https://img.shields.io/static/v1?label=Click&message=v8.1.3&color=purple)](#)
___

### The settings.json file in detail

So as I'm writting this doc, the full settings file looks like this:
```
{
    "rel_setup_path": ".local/bin",
    "rel_logs_path": ".local/logs",
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
        "history_limit": 2
    }
}
```

Let's dive into what these parameters do.

###### 1/ First, we have:

```"rel_setup_path"```, that is the setup path where the project will be installed by the setup script.

```"rel_logs_path```, which is used by the logging function that is defined in /tools/utils.py. It can be edited 
to specify where you want to store shlerp logs.

##### Note: These paths are relative to the home of the user you are currently using, so please ensure that you choose a location that is still under the home of your current user.


###### 2/ Then, the```"logging"``` section
lists parameters that are related to the logging behavior of shlerp. It is composed of two subsections:

- ```"prune"```, that corresponds to a smart logging management system that will keep only X log entries within a central log file.
- ```"no_prune"```, that corresponds to a "legacy" logging system. It basically creates a new log file each time the maximum log size is reached by the most recent log file.

Please note, the ```"prune"``` mode is the one that is enabled by default by the ```enabled``` parameter. It is so that you don't have to worry about your logs growing too large.

Setting ```"enabled"``` to false will make shlerp us the "legacy" logging mode that is only useful if you want to keep track of your old backup jobs at all times.

###### 3/ The ```"rules"``` section
only contains one parameter for now: ```"history_limit"```.
It sets the maximum length of preferred rules to look evaluate before switching to the whole ruleset at the rule detection step.
Please see the doc related to [matching rules](./rulesystem.md) if you need more details on this topic.

[Back to main README](https://github.com/synchronic777/shlerp-cli)