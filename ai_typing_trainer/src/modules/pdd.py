import os
import sys
import json
import time
import random
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sound

SAVES_DIR   = os.path.join(os.path.dirname(__file__), "..", "..", "saves")
STATS_PATH  = os.path.join(SAVES_DIR, "pdd.json")
_TR_DIR     = os.path.join(os.path.dirname(__file__), "..", "..", "..", "TrafficRules", "TrafficRules")
DB_PATH     = os.path.join(_TR_DIR, "tickets.db")
IMAGES_BASE = os.path.normpath(_TR_DIR)

import base64
import math

try:
    from PIL import Image as _PILImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    from term_image.image import from_file as _img_from_file
    _HAS_TERM_IMAGE = True
except ImportError:
    _HAS_TERM_IMAGE = False

_IS_WEZTERM = os.environ.get("TERM_PROGRAM") == "WezTerm"
_CELL_ASPECT = 0.5  # cell_width / cell_height ratio (~8px / 16px)

SESSION_SIZE = 10

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
WHITE  = "\033[37m"


# ── database ───────────────────────────────────────────────────────────────────

def load_tickets() -> list[dict]:
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, question_num, question_text, explanation, has_image, image_path FROM tickets ORDER BY id")
    tickets = []
    for row in cur.fetchall():
        cur.execute(
            "SELECT position, text, is_correct FROM options WHERE ticket_id=? ORDER BY position",
            (row["id"],)
        )
        options = [{"text": o["text"], "correct": bool(o["is_correct"])} for o in cur.fetchall()]
        if not any(o["correct"] for o in options):
            continue
        img_path = None
        if row["has_image"] and row["image_path"]:
            full = os.path.normpath(os.path.join(IMAGES_BASE, row["image_path"]))
            if os.path.exists(full):
                img_path = full
        tickets.append({
            "id": row["id"],
            "num": row["question_num"],
            "question": row["question_text"],
            "explanation": row["explanation"] or "",
            "image": img_path,
            "options": options,
        })
    conn.close()
    return tickets


# ── stats ──────────────────────────────────────────────────────────────────────

def load_stats() -> dict:
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH) as f:
            return json.load(f)
    return {}


def save_stats(stats: dict):
    os.makedirs(SAVES_DIR, exist_ok=True)
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)


def entry(stats: dict, tid: int) -> dict:
    key = str(tid)
    if key not in stats:
        stats[key] = {"correct": 0, "wrong": 0}
    return stats[key]


# ── question selection ─────────────────────────────────────────────────────────

def pick_session(tickets: list[dict], stats: dict, n: int = SESSION_SIZE) -> list[dict]:
    unseen, wrong, seen = [], [], []
    for t in tickets:
        e = stats.get(str(t["id"]), {"correct": 0, "wrong": 0})
        if e["correct"] == 0 and e["wrong"] == 0:
            unseen.append(t)
        elif e["wrong"] > 0:
            wrong.append(t)
        else:
            seen.append(t)

    random.shuffle(unseen)
    random.shuffle(wrong)
    random.shuffle(seen)

    chosen = (wrong + unseen + seen)[:n]
    random.shuffle(chosen)
    return chosen


# ── display ────────────────────────────────────────────────────────────────────

def progress_line(tickets: list[dict], stats: dict) -> str:
    total = len(tickets)
    correct_only = sum(1 for t in tickets
                       if stats.get(str(t["id"]), {}).get("correct", 0) > 0
                       and stats.get(str(t["id"]), {}).get("wrong", 0) == 0)
    wrong_any = sum(1 for t in tickets
                    if stats.get(str(t["id"]), {}).get("wrong", 0) > 0)
    seen = sum(1 for t in tickets
               if stats.get(str(t["id"]), {}).get("correct", 0) > 0
               or stats.get(str(t["id"]), {}).get("wrong", 0) > 0)
    pct = seen / total * 100 if total else 0
    return (f"  {DIM}Questions: {seen}/{total}  "
            f"{GREEN}✓ {correct_only}{RESET}  "
            f"{RED}✗ {wrong_any}{RESET}  "
            f"{DIM}({pct:.0f}%){RESET}")


def wrap(text: str, width: int = 72, indent: str = "  ") -> str:
    words = text.split()
    lines, line = [], []
    length = 0
    for w in words:
        if length + len(w) + (1 if line else 0) > width:
            lines.append(indent + " ".join(line))
            line, length = [w], len(w)
        else:
            if line:
                length += 1
            line.append(w)
            length += len(w)
    if line:
        lines.append(indent + " ".join(line))
    return "\n".join(lines)


def _image_height_rows(path: str, width_cols: int) -> int:
    if _HAS_PIL:
        try:
            with _PILImage.open(path) as img:
                w, h = img.size
            return max(1, math.ceil(h / w * width_cols * _CELL_ASPECT))
        except Exception:
            pass
    return 20


def _show_iterm2(path: str, width_cols: int = 40):
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    seq = f"\033]1337;File=inline=1;width={width_cols}:{b64}\007"
    height_rows = _image_height_rows(path, width_cols)
    sys.stdout.flush()
    sys.stdout.buffer.write(seq.encode("ascii"))
    sys.stdout.buffer.flush()
    sys.stdout.write("\n" * height_rows)
    sys.stdout.flush()


def show_image(path: str):
    if _IS_WEZTERM:
        try:
            _show_iterm2(path)
        except Exception:
            pass
    elif _HAS_TERM_IMAGE:
        try:
            img = _img_from_file(path)
            img.width = 40
            img.draw()
            print()
        except Exception:
            pass


def show_question(ticket: dict, idx: int, total: int, stats: dict):
    os.system("cls" if os.name == "nt" else "clear")
    print()
    e = stats.get(str(ticket["id"]), {"correct": 0, "wrong": 0})
    if e["correct"] == 0 and e["wrong"] == 0:
        hist = f"{WHITE}new{RESET}"
    elif e["wrong"] > 0:
        hist = f"{RED}wrong: {e['wrong']}{RESET}"
    else:
        hist = f"{GREEN}✓ {e['correct']}x{RESET}"

    num_str = f"#{ticket['num']}" if ticket["num"] else f"id{ticket['id']}"
    print(f"  {DIM}[{idx}/{total}  {num_str}]{RESET}  {hist}")
    print()

    if ticket["image"]:
        show_image(ticket["image"])

    print(wrap(ticket["question"]))
    print()
    for i, opt in enumerate(ticket["options"], 1):
        print(f"  {BOLD}{i}.{RESET} {opt['text']}")
    print()


# ── session ────────────────────────────────────────────────────────────────────

def run_session(tickets: list[dict], stats: dict) -> tuple[int, int]:
    session = pick_session(tickets, stats)
    correct_count = 0

    for i, ticket in enumerate(session, 1):
        show_question(ticket, i, len(session), stats)

        while True:
            try:
                raw = input("  > ").strip()
            except EOFError:
                return correct_count, i - 1
            if raw in ("1", "2", "3", "4"):
                break

        chosen_idx = int(raw) - 1
        chosen = ticket["options"][chosen_idx]
        correct_idx = next(j for j, o in enumerate(ticket["options"]) if o["correct"])
        is_correct = chosen["correct"]

        e = entry(stats, ticket["id"])
        if is_correct:
            e["correct"] += 1
            sound.play_fixed()
            print(f"\n  {GREEN}{BOLD}✓ Correct!{RESET}")
            correct_count += 1
        else:
            e["wrong"] += 1
            sound.play_error()
            correct_text = ticket["options"][correct_idx]["text"]
            print(f"\n  {RED}{BOLD}✗ Wrong.{RESET}  "
                  f"{DIM}Correct answer:{RESET} {BOLD}{correct_idx + 1}. {correct_text}{RESET}")

        if ticket["explanation"]:
            print()
            print(f"  {DIM}Explanation:{RESET}")
            print(wrap(ticket["explanation"], width=70))

        print()
        try:
            input(f"  {DIM}[Enter] → next{RESET}")
        except EOFError:
            break

    return correct_count, len(session)


# ── main menu ──────────────────────────────────────────────────────────────────

def run(cfg: dict):
    tickets = load_tickets()
    if not tickets:
        print(f"\n  {RED}Database not found:{RESET}\n  {DB_PATH}")
        input("\n  [Enter]")
        return

    stats = load_stats()

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {BOLD}Traffic Rules{RESET}")
        print()
        print(progress_line(tickets, stats))
        print()
        print(f"  1. Train ({SESSION_SIZE} questions)")
        print(f"  0. Back")
        print()

        try:
            choice = input("  > ").strip()
        except EOFError:
            break

        if choice == "0":
            break
        elif choice == "1":
            correct, total = run_session(tickets, stats)
            save_stats(stats)
            os.system("cls" if os.name == "nt" else "clear")
            pct = correct / total * 100 if total else 0
            print(f"\n  {BOLD}Result:{RESET} {correct}/{total}  ({pct:.0f}%)")
            if pct == 100:
                print(f"  {GREEN}Excellent!{RESET}")
            elif pct >= 80:
                print(f"  {CYAN}Good!{RESET}")
            else:
                print(f"  {YELLOW}Need to repeat.{RESET}")
            print()
            try:
                input(f"  {DIM}[Enter] → menu{RESET}")
            except EOFError:
                break
