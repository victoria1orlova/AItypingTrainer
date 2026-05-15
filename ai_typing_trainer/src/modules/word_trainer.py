import os
import sys
import json
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sound
import i18n
from input_tracker import read_word

WORDS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "words")
SAVES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "saves")
PROBLEMS_PATH = os.path.join(SAVES_DIR, "word_problems.json")


# ── persistence ───────────────────────────────────────────────────────────────

def load_sets() -> list[dict]:
    sets = []
    for fname in sorted(os.listdir(WORDS_DIR)):
        if fname.endswith(".json"):
            with open(os.path.join(WORDS_DIR, fname)) as f:
                sets.append(json.load(f))
    return sets


def load_problems() -> dict:
    if os.path.exists(PROBLEMS_PATH):
        with open(PROBLEMS_PATH) as f:
            return json.load(f)
    return {}


def save_problems(problems: dict):
    os.makedirs(SAVES_DIR, exist_ok=True)
    with open(PROBLEMS_PATH, "w") as f:
        json.dump(problems, f, indent=2, ensure_ascii=False)


def save_result(name: str, wpm: float, accuracy: float, theme: str):
    os.makedirs(SAVES_DIR, exist_ok=True)
    path = os.path.join(SAVES_DIR, "word_trainer.json")
    history = []
    if os.path.exists(path):
        with open(path) as f:
            history = json.load(f)
    history.append({
        "user": name,
        "theme": theme,
        "wpm": round(wpm, 1),
        "accuracy": round(accuracy, 1),
        "time": time.strftime("%Y-%m-%d %H:%M"),
    })
    with open(path, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ── helpers ───────────────────────────────────────────────────────────────────

def diff_highlight(expected: str, typed: str) -> str:
    result = []
    for i, ch in enumerate(expected):
        if i < len(typed):
            result.append(typed[i] if typed[i] == ch else f"\033[31m{typed[i]}\033[0m")
        else:
            result.append("\033[31m_\033[0m")
    if len(typed) > len(expected):
        result.append(f"\033[31m{typed[len(expected):]}\033[0m")
    return "".join(result)


def pick_words(all_words: list[str], problems: dict, count: int = 10) -> list[str]:
    problem_words = [w for w in all_words if w in problems and problems[w] > 0]
    problem_words.sort(key=lambda w: problems[w], reverse=True)

    slots_for_problems = min(len(problem_words), count // 3)
    chosen = problem_words[:slots_for_problems]

    remaining = [w for w in all_words if w not in chosen]
    random.shuffle(remaining)
    chosen += remaining[: count - len(chosen)]
    random.shuffle(chosen)
    return chosen


# ── main ──────────────────────────────────────────────────────────────────────

def run(cfg: dict):
    sets = load_sets()
    if not sets:
        print("No word sets found.")
        input("Enter...")
        return

    print(f"\n{i18n.t('word_title')}\n")
    print(f"{i18n.t('word_pick_theme')}:")
    for i, s in enumerate(sets, 1):
        print(f"  {i}. {s['name']}")
    print(f"  0. {i18n.t('word_back')}\n")

    choice = input(f"{i18n.t('word_prompt')}: ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    idx = int(choice) - 1
    if idx >= len(sets):
        return

    word_set = sets[idx]
    problems = load_problems()
    words = pick_words(word_set["words"], problems, count=10)

    print(f"\n{i18n.t('word_session_info', theme=word_set['name'], count=len(words))}")

    problem_count = sum(1 for w in words if w in problems and problems[w] > 0)
    if problem_count:
        print(i18n.t("word_problems_included", count=problem_count))

    print()
    input(f"{i18n.t('word_start_prompt')}\n")

    correct = 0
    start = time.time()

    for i, en in enumerate(words, 1):
        errors = problems.get(en, 0)
        flag = f" ({'⚠ ' * min(errors, 3)}{i18n.t('word_errors_flag', count=errors)})" if errors else ""

        print(f"[{i}/{len(words)}]  \033[1m{en}\033[0m{flag}")
        typed, had_corrections = read_word()
        typed = typed.strip()

        was_problem = problems.get(en, 0) > 0

        if typed == en:
            if had_corrections:
                print(f"      \033[33m{i18n.t('word_correct')} ~\033[0m\n")
                problems[en] = problems.get(en, 0) + 1  # soft penalty: needed corrections
            else:
                print(f"      \033[32m{i18n.t('word_correct')}\033[0m\n")
                if was_problem:
                    sound.play_fixed()
                    problems[en] = max(0, problems[en] - 1)
            correct += 1
        else:
            sound.play_error()
            highlighted = diff_highlight(en, typed)
            print(f"      \033[31m{i18n.t('word_wrong', typed=highlighted)}\033[0m")
            print(f"         {i18n.t('word_correct_was', word=chr(27) + '[32m' + en + chr(27) + '[0m')}\n")
            problems[en] = problems.get(en, 0) + 2

    elapsed = time.time() - start
    total_chars = sum(len(w) for w in words)
    wpm = (total_chars / 5) / (elapsed / 60)
    accuracy = (correct / len(words)) * 100

    print("─" * 34)
    print(f"  {i18n.t('word_result_wpm', wpm=f'{wpm:.1f}')}")
    print(f"  {i18n.t('word_result_acc', acc=f'{accuracy:.1f}', correct=correct, total=len(words))}")
    print(f"  {i18n.t('word_result_time', sec=f'{elapsed:.1f}')}")

    top_problems = sorted(problems.items(), key=lambda x: x[1], reverse=True)[:5]
    top_problems = [(w, s) for w, s in top_problems if s > 0]
    if top_problems:
        print(f"\n  {i18n.t('word_problem_words')}")
        for w, s in top_problems:
            print(f"    {w}  ({i18n.t('word_errors_flag', count=s)})")

    print("─" * 34)

    save_problems(problems)
    save_result(cfg.get("name", "User"), wpm, accuracy, word_set["name"])
    input(f"\n{i18n.t('word_return')}")
