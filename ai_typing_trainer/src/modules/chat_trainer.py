import os
import sys
import json
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import i18n

CHAT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chat")


def load_json(fname: str) -> list:
    with open(os.path.join(CHAT_DIR, fname), encoding="utf-8") as f:
        return json.load(f)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ── Mode 1: Reading Speed ─────────────────────────────────────────────────────

def mode_reading():
    texts = load_json("texts.json")
    random.shuffle(texts)
    texts = texts[:5]

    scores = []
    for item in texts:
        clear()
        print(f"\n{item['text']}\n")
        input(i18n.t("chat_reading_read"))

        clear()
        raw = input(i18n.t("chat_reading_keywords")).strip().lower().split()
        typed = set(raw)
        keywords = set(item["keywords"])

        correct = len(typed & keywords)
        missed = keywords - typed
        scores.append((correct, len(keywords)))

        print(f"\n{i18n.t('chat_reading_score', correct=correct, total=len(keywords))}")
        if missed:
            print(i18n.t("chat_reading_missed", words=", ".join(sorted(missed))))
        input(f"\n{i18n.t('chat_next')}")

    total_correct = sum(c for c, _ in scores)
    total_kw = sum(t for _, t in scores)
    clear()
    print(f"\n{i18n.t('chat_result_title')}")
    print(f"  {i18n.t('chat_reading_score', correct=total_correct, total=total_kw)}")
    input(f"\n{i18n.t('chat_return')}")


# ── Mode 2: Quick Responses ───────────────────────────────────────────────────

def mode_quick():
    prompts = load_json("quick.json")
    random.shuffle(prompts)
    prompts = prompts[:7]

    times = []
    wpms = []

    for prompt in prompts:
        clear()
        print(f"\n  💬 {prompt}\n")
        start = time.time()
        response = input(i18n.t("chat_quick_prompt")).strip()
        elapsed = time.time() - start

        if response:
            wpm = (len(response) / 5) / (elapsed / 60)
            wpms.append(wpm)
            times.append(elapsed)
            print(f"  {i18n.t('chat_quick_time', sec=f'{elapsed:.1f}', wpm=f'{wpm:.0f}')}")
        input(f"\n{i18n.t('chat_next')}")

    if wpms:
        clear()
        avg_wpm = sum(wpms) / len(wpms)
        avg_time = sum(times) / len(times)
        print(f"\n{i18n.t('chat_result_title')}")
        print(f"  {i18n.t('chat_quick_time', sec=f'{avg_time:.1f}', wpm=f'{avg_wpm:.0f}')} (avg)")
    input(f"\n{i18n.t('chat_return')}")


# ── Mode 3: AI Dialog ─────────────────────────────────────────────────────────

def mode_dialog():
    dialogs = load_json("dialogs.json")
    dialog = random.choice(dialogs)

    clear()
    print(f"\n{i18n.t('chat_dialog_topic', topic=dialog['topic'])}\n")
    input(i18n.t("chat_next"))

    times = []
    for exchange in dialog["exchanges"]:
        clear()
        print(f"\n{i18n.t('chat_dialog_topic', topic=dialog['topic'])}\n")
        print(f"{i18n.t('chat_dialog_bot', msg=exchange['bot'])}\n")
        start = time.time()
        input(i18n.t("chat_dialog_you"))
        elapsed = time.time() - start
        times.append(elapsed)

    clear()
    avg = sum(times) / len(times) if times else 0
    print(f"\n{i18n.t('chat_result_title')}")
    print(f"  Avg response time: {avg:.1f}s")
    input(f"\n{i18n.t('chat_return')}")


# ── Menu ──────────────────────────────────────────────────────────────────────

def run(cfg: dict):
    modes = [
        (i18n.t("chat_mode_reading"), mode_reading),
        (i18n.t("chat_mode_quick"),   mode_quick),
        (i18n.t("chat_mode_dialog"),  mode_dialog),
    ]

    while True:
        clear()
        print(f"\n{i18n.t('chat_title')}\n")
        for i, (name, _) in enumerate(modes, 1):
            print(f"  {i}. {name}")
        print(f"  0. {i18n.t('chat_back')}\n")

        choice = input(f"{i18n.t('chat_prompt')}: ").strip()
        if choice == "0":
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(modes):
            _, fn = modes[int(choice) - 1]
            try:
                fn()
            except KeyboardInterrupt:
                pass
