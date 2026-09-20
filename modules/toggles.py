import json
import os

SETTINGS_FILE = "modulos.json"

DEFAULT_STATE = {
    "moderacion": True,
    "biblioteca": True,
    "pedidos": True,
    "entradas": True
}

def load_toggles():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_STATE.copy()
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_STATE.copy()

def save_toggles(state):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(state, f)

def is_enabled(module_name):
    return load_toggles().get(module_name, True)

def toggle_module(module_name):
    state = load_toggles()
    if module_name in state:
        state[module_name] = not state[module_name]
        save_toggles(state)
        return state[module_name]
    return False
