import json
import os

_LANG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "lang")
_strings: dict = {}


def load(lang: str = "en"):
    global _strings
    path = os.path.join(_LANG_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(_LANG_DIR, "en.json")
    with open(path, encoding="utf-8") as f:
        _strings = json.load(f)


def t(key: str, **kwargs) -> str:
    text = _strings.get(key, key)
    return text.format(**kwargs) if kwargs else text


def available() -> list[dict]:
    langs = []
    for fname in sorted(os.listdir(_LANG_DIR)):
        if fname.endswith(".json"):
            with open(os.path.join(_LANG_DIR, fname), encoding="utf-8") as f:
                data = json.load(f)
                langs.append({"code": data["lang"], "name": data["lang_name"]})
    return langs
