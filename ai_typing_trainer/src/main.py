#!/usr/bin/env python3
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", write_through=True)
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

import config
import i18n
from modules import word_trainer, chat_trainer, listening, motivation, multiplication

MODULES = [
    ("Word Trainer",        word_trainer.run),
    ("Chat Trainer",        chat_trainer.run),
    ("Multiplication",      multiplication.run),
    ("Listening",           listening.run),
    ("Motivation",          motivation.run),
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def first_run_setup() -> dict:
    """Ask name and language on first launch."""
    # Load default lang to show setup in that lang (en by default)
    i18n.load("en")
    clear()
    print(f"\n{i18n.t('setup_welcome')}\n")

    # Pick language first
    langs = i18n.available()
    print(f"{i18n.t('setup_lang_prompt')}:")
    for i, lang in enumerate(langs, 1):
        print(f"  {i}. {lang['name']}")
    choice = input("\n: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(langs):
        lang_code = langs[int(choice) - 1]["code"]
    else:
        lang_code = "en"
    i18n.load(lang_code)

    clear()
    print(f"\n{i18n.t('setup_welcome')}\n")
    name = input(i18n.t("setup_name_prompt")).strip() or "User"

    cfg = {"name": name, "level": 1, "lang": lang_code}
    config.save(cfg)

    print(f"\n{i18n.t('setup_done')}")
    input()
    return cfg


def settings_menu(cfg: dict):
    langs = i18n.available()
    while True:
        clear()
        print(f"\n{i18n.t('settings_title')}\n")
        print(f"  1. {i18n.t('settings_change_name', name=cfg['name'])}")
        print(f"  2. {i18n.t('settings_change_lang', lang=cfg['lang'])}")
        print(f"  0. {i18n.t('settings_back')}\n")

        choice = input(": ").strip()
        if choice == "0":
            break
        elif choice == "1":
            name = input(i18n.t("settings_name_prompt")).strip()
            if name:
                cfg["name"] = name
                config.save(cfg)
                print(i18n.t("settings_saved"))
                input()
        elif choice == "2":
            print(f"\n{i18n.t('settings_lang_prompt')}:")
            for i, lang in enumerate(langs, 1):
                print(f"  {i}. {lang['name']}")
            lc = input("\n: ").strip()
            if lc.isdigit() and 1 <= int(lc) <= len(langs):
                cfg["lang"] = langs[int(lc) - 1]["code"]
                i18n.load(cfg["lang"])
                config.save(cfg)
                print(i18n.t("settings_saved"))
                input()


def main():
    if not config.exists():
        cfg = first_run_setup()
    else:
        cfg = config.load()

    i18n.load(cfg.get("lang", "en"))
    clear()

    while True:
        clear()
        print(f"{i18n.t('menu_title')} ({i18n.t('menu_greeting', name=cfg['name'])})\n")
        for i, (name, _) in enumerate(MODULES, 1):
            print(f"  {i}. {name}")
        print(f"  s. {i18n.t('menu_settings')}")
        print(f"  0. {i18n.t('menu_exit')}\n")

        choice = input(f"{i18n.t('menu_prompt')}: ").strip().lower()

        if choice == "0":
            print(i18n.t("bye"))
            break
        elif choice == "s":
            settings_menu(cfg)
        elif choice.isdigit() and 1 <= int(choice) <= len(MODULES):
            _, fn = MODULES[int(choice) - 1]
            clear()
            try:
                fn(cfg)
            except KeyboardInterrupt:
                pass
        else:
            input(i18n.t("menu_invalid"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{i18n.t('bye')}")
