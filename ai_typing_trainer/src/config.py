import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "user_config.json")

DEFAULTS = {"name": None, "level": 1, "lang": "en"}


def exists() -> bool:
    return os.path.exists(CONFIG_PATH)


def load() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return dict(DEFAULTS)


def save(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
