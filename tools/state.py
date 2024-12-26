from tools.utils import get_settings

_state = {
    'uid': '', # UID that represents the current execution. Not meant to be changed after its initial initialization
    'step': [], # Represents the step we're in, will be used if a SIGINT occurs
    'verbose': get_settings()['verbose'], # Defines if the printing function should overwrite the previous term line or not
    'backed_up': [], # Lists successfully backed up projects path
    'failures': [], # Lists the projects that couldn't be backed up
    'ad_failures': [], # Lists the paths for which the autodetection failed
    'upload_failures': [], # Lists the paths for which the upload failed
    'total': 0 # Total number of projects to backup
}


# Getters

def state(key):
    return _state.get(key)


def get_step():
    return _state['step'][-1]


def x_consecutive_entries_in_step(x, step):
    count = 0
    if len(_state['step']) >= x:
        if _state['step'][-1] == step:
            for entry in _state['step'][::-1]:
                if entry == step:
                    count += 1
                else:
                    break
        else:
            return False
        return True if count >= x else False


# Setters

def set_state(key, value):
    _state[key] = value


def append_state(key, value):
    _state[key].append(value)


def incr_state(key, amount=1):
    _state[key] += amount


def set_step(step):
    _state['step'].append(step)
    if len(_state['step']) > 3:
        _state['step'].pop(0)


def flush_steps():
    global _state
    _state['step'] = []


def force_verbose():
    if not _state['verbose']:
        _state['verbose'] = True