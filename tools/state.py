_state = {
    'uid': '', # UID that represents the current execution. Not meant to be changed after its initial initialization
    'step': '', # Represents the step we're in, will be used if a SIGINT occurs
    'backed_up': [], # Lists successfully backed up projects path
    'failures': [], # Lists the projects that couldn't be backed up
    'ad_failures': [], # Lists the paths for which the autodetection failed
    'upload_failures': [], # Lists the paths for which the upload failed
    'total': 0 # Total number of projects to backup
}

def state(key):
    return _state.get(key)

def set_state(key, value):
    _state[key] = value

def append_state(key, value):
    _state[key].append(value)

def incr_state(key, amount=1):
    _state[key] += amount
