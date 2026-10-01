"""Control actions and state for the web interface

Actions are registered with @action and run through run_action(), which
returns None on success or an error message. Anything that changes state
calls notify() so connected clients get the new state.
"""
import glob
import json
import os
import re
import threading

import numpy

_actions = {}
_listeners = []
_lock = threading.Lock()

# Effects whose options live under a different key in effect_opts
EFFECT_CONFIG_KEYS = {"Reactive Runner": "RunnerReactive"}

PROFILES_DIR = "profiles"


def setConfig(config):
    global _config
    _config = config


def setBoards(boards):
    global _boards
    _boards = boards


def setAudio(audio_input):
    global _audio
    _audio = audio_input


def action(name):
    def wrapper(func):
        _actions[name] = func
        return func
    return wrapper


def on_change(listener):
    _listeners.append(listener)


def notify():
    for listener in _listeners:
        listener()


def run_action(name, payload):
    if name not in _actions:
        return "Unknown action: {}".format(name)
    if not isinstance(payload, dict):
        return "Payload must be an object"
    try:
        with _lock:
            error = _actions[name](payload)
    except (KeyError, TypeError, ValueError) as e:
        return "{}: {}".format(type(e).__name__, e)
    if error is None:
        notify()
    return error


# State

def _effect_config_key(effect):
    return EFFECT_CONFIG_KEYS.get(effect, effect)


def _effect_options(board, effect):
    options = []
    for option in board.visualizer.dynamic_effects_config.get(_effect_config_key(effect), []):
        config_ = option[3] if len(option) > 3 else None
        if isinstance(config_, dict):
            # Colour / gradient dropdowns only need their names
            config_ = list(config_)
        options.append({"key": option[0], "label": option[1], "type": option[2], "config": config_})
    return options


def _device_state(name, board):
    effects = []
    for effect, implementation in board.visualizer.effects.items():
        effects.append({
            "name": effect,
            "reactive": not implementation.nonReactive,
            "options": _effect_options(board, effect),
            "values": board.effectConfig.get(_effect_config_key(effect), {}),
        })
    return {
        "name": name,
        "leds": board.config["N_PIXELS"],
        "currentEffect": board.config["current_effect"],
        "minFrequency": board.config["MIN_FREQUENCY"],
        "maxFrequency": board.config["MAX_FREQUENCY"],
        "layout": _config.settings["devices"][name].get("layout"),
        "effects": effects,
    }


def get_state():
    from lib.audio import available_sources
    return {
        "sync": _config.settings["sync"],
        "brightness": round(_config.settings["brightness"] * 100),
        "currentProfile": _config.settings["currentProfile"],
        "profiles": get_profiles(),
        "audio": {
            "source": _audio.source,
            "error": _audio.error,
            "sources": available_sources(),
        },
        "room": _config.settings.get("room"),
        "devices": [_device_state(name, board) for name, board in _boards.items()],
    }


def to_json(data):
    def default(value):
        # numpy scalars from effect options
        if isinstance(value, numpy.generic):
            return value.item()
        raise TypeError("Not serializable: {!r}".format(value))
    return json.dumps(data, default=default)


# Helpers

def _target_boards(device):
    """Boards an edit applies to: all of them when synced, otherwise one"""
    if device not in _boards:
        raise ValueError("Device not found: {}".format(device))
    if _config.settings["sync"]:
        return list(_boards.values())
    return [_boards[device]]


def _clear_profile():
    _config.settings["currentProfile"] = ""


def _coerce(current, value):
    """Cast an incoming value to the type of the option it replaces"""
    if isinstance(current, bool):
        if not isinstance(value, bool):
            raise TypeError("Expected true or false")
        return value
    if isinstance(current, (int, numpy.integer)) and not isinstance(current, bool):
        return int(value)
    if isinstance(current, (float, numpy.floating)):
        return float(value)
    return str(value)


def _profile_id(name):
    profile_id = re.sub(r"[^a-z0-9.-]+", "", name.lower())
    if not profile_id or profile_id.startswith("."):
        raise ValueError("Profile name needs at least one letter or number")
    return profile_id


def get_profiles():
    profiles = []
    for path in sorted(glob.glob(os.path.join(PROFILES_DIR, "*.json"))):
        with open(path) as f:
            data = json.load(f)
        profiles.append({"id": os.path.splitext(os.path.basename(path))[0], "name": data.get("name")})
    return profiles


# Actions

@action("set-effect")
def set_effect(payload):
    effect = payload["effect"]
    boards = _target_boards(payload["device"])
    if effect not in boards[0].visualizer.effects:
        return "Effect not found: {}".format(effect)
    for board in boards:
        board.config["current_effect"] = effect
    _clear_profile()


@action("set-option")
def set_option(payload):
    effect = _effect_config_key(payload["effect"])
    option = payload["option"]
    for board in _target_boards(payload["device"]):
        if option not in board.effectConfig.get(effect, {}):
            return "Effect option not found: {} {}".format(effect, option)
        board.effectConfig[effect][option] = _coerce(board.effectConfig[effect][option], payload["value"])
    _clear_profile()


@action("set-brightness")
def set_brightness(payload):
    value = int(payload["value"])
    if not 0 <= value <= 100:
        return "Brightness must be between 0 and 100"
    _config.settings["brightness"] = value / 100.0
    _clear_profile()


@action("set-sync")
def set_sync(payload):
    if not isinstance(payload["value"], bool):
        return "Expected true or false"
    _config.settings["sync"] = payload["value"]
    _clear_profile()


@action("set-frequency")
def set_frequency(payload):
    low, high = int(payload["min"]), int(payload["max"])
    if not 0 <= low < high <= 24000:
        return "Frequencies must satisfy 0 <= min < max <= 24000"
    for board in _target_boards(payload["device"]):
        board.config["MIN_FREQUENCY"] = low
        board.config["MAX_FREQUENCY"] = high
        board.signalProcessor.create_mel_bank()
    _clear_profile()


@action("set-audio")
def set_audio(payload):
    _audio.set_source(payload["source"])


@action("save-profile")
def save_profile(payload):
    name = str(payload["name"]).strip()[:40]
    profile_id = _profile_id(name)
    data = {
        "name": name,
        "settings": {
            "brightness": _config.settings["brightness"],
            "sync": _config.settings["sync"],
        },
        "devices": {device: board.getProfile() for device, board in _boards.items()},
    }
    os.makedirs(PROFILES_DIR, exist_ok=True)
    with open(os.path.join(PROFILES_DIR, profile_id + ".json"), "w") as f:
        f.write(to_json(data))
    _config.settings["currentProfile"] = profile_id


@action("load-profile")
def load_profile(payload):
    profile_id = _profile_id(payload["id"])
    path = os.path.join(PROFILES_DIR, profile_id + ".json")
    if not os.path.isfile(path):
        return "Profile not found: {}".format(profile_id)
    with open(path) as f:
        data = json.load(f)
    _config.settings["brightness"] = data["settings"]["brightness"]
    _config.settings["sync"] = data["settings"]["sync"]
    for device, profile in data["devices"].items():
        if device in _boards:
            _boards[device].setProfile(profile)
    _config.settings["currentProfile"] = profile_id


@action("delete-profile")
def delete_profile(payload):
    profile_id = _profile_id(payload["id"])
    path = os.path.join(PROFILES_DIR, profile_id + ".json")
    if not os.path.isfile(path):
        return "Profile not found: {}".format(profile_id)
    os.remove(path)
    if _config.settings["currentProfile"] == profile_id:
        _clear_profile()
