import json
import os
from typing import List, Dict, Any

PRESETS_PATH = "data/presets.json"


def _load_all() -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(PRESETS_PATH):
        return {}
    try:
        with open(PRESETS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data: Dict[str, List[Dict[str, Any]]]):
    os.makedirs(os.path.dirname(PRESETS_PATH), exist_ok=True)
    with open(PRESETS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_presets(user_id: str) -> List[Dict[str, Any]]:
    data = _load_all()
    return data.get(user_id, [])


def add_preset(user_id: str, preset: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = _load_all()
    arr = data.get(user_id, [])
    arr.append(preset)
    data[user_id] = arr
    _save_all(data)
    return arr
