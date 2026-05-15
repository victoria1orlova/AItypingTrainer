import os
import sys
import json
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import i18n
import sound

SAVES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "saves")
STATS_PATH = os.path.join(SAVES_DIR, "multiplication.json")

TARGET_TIME = 2.0
SLOW_TIME   = 5.0

RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"


# ── persistence ───────────────────────────────────────────────────────────────

def load_stats() -> dict:
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH) as f:
            return json.load(f)
    stats = {}
    for a in range(1, 11):
        for b in range(1, 11):
            stats[f"{a}x{b}"] = {"correct": 0, "wrong": 0, "avg_time": 0.0}
    return stats


def save_stats(stats: dict):
    os.makedirs(SAVES_DIR, exist_ok=True)
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)


def update_avg(old_avg: float, count: int, new_time: float) -> float:
    return (old_avg * count + new_time) / (count + 1)


# ── colors ────────────────────────────────────────────────────────────────────

def cell_color(entry: dict) -> str:
    if entry["correct"] == 0:
        return "\033[37m"
    t = entry["avg_time"]
    if t > SLOW_TIME:       return "\033[31m"
    if t > TARGET_TIME * 1.5: return "\033[33m"
    if t > TARGET_TIME:     return "\033[36m"
    return "\033[32m"


# ── full table (shown before session) ────────────────────────────────────────

def show_table(stats: dict):
    os.system("cls" if os.name == "nt" else "clear")
    header = "    " + "".join(f"  {b:2d}" for b in range(1, 11))
    print(f"\n{BOLD}{header}{RESET}")
    print("    " + "─" * 42)
    for a in range(1, 11):
        row = f"{BOLD}{a:2d}{RESET} │"
        for b in range(1, 11):
            e = stats[f"{a}x{b}"]
            row += f"{cell_color(e)} {a*b:3d}{RESET}"
        times = [stats[f"{a}x{b}"]["avg_time"] for b in range(1, 11)
                 if stats[f"{a}x{b}"]["correct"] > 0]
        row += f"  {DIM}{sum(times)/len(times):.1f}s{RESET}" if times else ""
        print(row)
    print(f"\n{DIM}white=unseen  yellow=slow  cyan=ok  green=fast (<{TARGET_TIME}s){RESET}")


# ── compact top-3 panel (shown during session) ────────────────────────────────

def top_problems(stats: dict, n: int = 3) -> list[tuple[int, int]]:
    candidates = []
    for a in range(1, 11):
        for b in range(1, 11):
            e = stats[f"{a}x{b}"]
            if e["correct"] == 0:
                continue  # unseen — not a problem yet
            if e["wrong"] > 0:
                score = 500 + e["wrong"] * 10
            elif e["avg_time"] > TARGET_TIME:
                score = e["avg_time"]
            else:
                continue  # fast and correct — not a problem
            candidates.append((score, a, b))
    candidates.sort(reverse=True)
    return [(a, b) for _, a, b in candidates[:n]]


def render_top_panel(stats: dict) -> str:
    problems = top_problems(stats)
    if not problems:
        return f"  {DIM}No problem examples ✓{RESET}"
    lines = [f"  {DIM}Top problems:{RESET}"]
    for (a, b) in problems:
        e = stats[f"{a}x{b}"]
        color = cell_color(e)
        if e["correct"] == 0:
            info = "new"
        elif e["wrong"] > 0:
            info = f"errors: {e['wrong']}"
        else:
            info = f"avg {e['avg_time']:.1f}s"
        lines.append(f"  {color}{a} × {b} = {a*b}{RESET}  {DIM}({info}){RESET}")
    return "\n".join(lines)


# ── session ───────────────────────────────────────────────────────────────────

def pick_examples(stats: dict, count: int = 15) -> list[tuple[int, int]]:
    unseen, slow, ok = [], [], []
    for a in range(1, 11):
        for b in range(1, 11):
            e = stats[f"{a}x{b}"]
            if e["correct"] == 0:
                unseen.append((a, b))
            elif e["avg_time"] > TARGET_TIME or e["wrong"] > 0:
                slow.append((a, b))
            else:
                ok.append((a, b))
    random.shuffle(unseen)
    random.shuffle(slow)
    random.shuffle(ok)
    chosen = (unseen + slow + ok)[:count]
    random.shuffle(chosen)
    return chosen


def run_session(stats: dict) -> tuple[dict, int, int]:
    examples = pick_examples(stats)
    correct_count = 0

    for i, (a, b) in enumerate(examples, 1):
        os.system("cls" if os.name == "nt" else "clear")
        print()
        print(render_top_panel(stats))
        print()

        e = stats[f"{a}x{b}"]
        hint = f"{DIM}avg {e['avg_time']:.1f}s{RESET}" if e["correct"] > 0 else f"{DIM}new{RESET}"

        print(f"  [{i}/{len(examples)}]  {hint}")
        print(f"\n  {BOLD}{a} × {b} = ?{RESET}\n")

        start = time.time()
        try:
            answer = input("  > ").strip()
        except EOFError:
            break
        elapsed = time.time() - start

        if answer.lstrip("-").isdigit() and int(answer) == a * b:
            sound.play_fixed()
            print(f"\n  \033[32m✓  {elapsed:.2f}s{RESET}")
            e["avg_time"] = round(update_avg(e["avg_time"], e["correct"], elapsed), 3)
            e["correct"] += 1
            correct_count += 1
        else:
            sound.play_error()
            print(f"\n  \033[31m✗  {a} × {b} = {a*b}{RESET}")
            e["wrong"] += 1
            e["avg_time"] = 0.0

        time.sleep(0.6)

    return stats, correct_count, len(examples)


# ── main ──────────────────────────────────────────────────────────────────────

def run(cfg: dict):
    stats = load_stats()

    while True:
        show_table(stats)
        print(f"\n  1. {i18n.t('mul_train')}")
        print(f"  0. {i18n.t('mul_back')}\n")

        choice = input("  > ").strip()
        if choice == "0":
            break
        elif choice == "1":
            stats, correct, total = run_session(stats)
            save_stats(stats)
            os.system("cls" if os.name == "nt" else "clear")
            accuracy = correct / total * 100 if total else 0
            print(f"\n  {i18n.t('mul_result', correct=correct, total=total, acc=f'{accuracy:.0f}')}")
            mastered = sum(
                1 for a in range(1, 11) for b in range(1, 11)
                if stats[f"{a}x{b}"]["correct"] > 0
                and stats[f"{a}x{b}"]["avg_time"] <= TARGET_TIME
                and stats[f"{a}x{b}"]["wrong"] == 0
            )
            print(f"  {i18n.t('mul_mastered', count=mastered, total=100)}")
            input(f"\n  {i18n.t('mul_continue')}")
