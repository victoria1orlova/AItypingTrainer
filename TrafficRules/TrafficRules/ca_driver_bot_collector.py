"""
Traffic Rules ticket collector for @ca_driver_bot (Telegram).
==============================================================

Walks the bot's quiz, captures every unique question with its options,
correct answer, explanation and image, and stores them in a local SQLite
database.

Requirements:
    pip install telethon

Setup:
    1. Visit https://my.telegram.org
    2. Sign in with your phone number.
    3. Open "API development tools" and create an application.
    4. Copy `credentials.py.example` to `credentials.py` and paste
       your `api_id` and `api_hash` into it.

Run:
    python ca_driver_bot_collector.py
"""

import asyncio
import os
import re
import sqlite3
import sys

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaPhoto

try:
    from credentials import API_ID, API_HASH
except ImportError:
    print(
        "ERROR: credentials.py not found.\n"
        "Copy credentials.py.example to credentials.py and fill in "
        "your Telegram API id/hash."
    )
    sys.exit(1)

# ============================================================
# Settings
# ============================================================
BOT_USERNAME = "@ca_driver_bot"

DB_FILE = "tickets.db"
IMAGES_DIR = "ticket_images"
DELAY = 2.0          # pause between bot requests (seconds), minimum 1.5
LIMIT = 500          # max new questions per session (0 = unlimited)
# ============================================================


# ── Database ────────────────────────────────────────────────

def db_connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def db_init():
    with db_connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                question_num INTEGER,
                question_text TEXT NOT NULL UNIQUE,
                explanation  TEXT DEFAULT '',
                has_image    INTEGER DEFAULT 0,
                image_path   TEXT,
                raw_text     TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS options (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id  INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                position   INTEGER NOT NULL,
                text       TEXT NOT NULL,
                is_correct INTEGER NOT NULL DEFAULT 0
            );
        """)


def db_load_seen() -> set:
    """Return the set of question_text values already stored."""
    with db_connect() as con:
        rows = con.execute("SELECT question_text FROM tickets").fetchall()
    return {r["question_text"] for r in rows}


def db_save_ticket(parsed: dict, options: list, image_path: str | None) -> bool:
    """
    Save a ticket. Returns True if newly inserted, False if it was a duplicate.
    Deduplication relies on the UNIQUE constraint on question_text.
    """
    with db_connect() as con:
        cur = con.execute(
            """INSERT OR IGNORE INTO tickets
               (question_num, question_text, explanation, has_image, image_path, raw_text)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                parsed["question_num"],
                parsed["question_text"],
                parsed["explanation"],
                1 if image_path else 0,
                image_path,
                parsed["raw_text"],
            ),
        )
        if cur.lastrowid == 0:
            return False
        ticket_id = cur.lastrowid
        con.executemany(
            "INSERT INTO options (ticket_id, position, text, is_correct) VALUES (?, ?, ?, ?)",
            [
                (ticket_id, i, o["text"], 1 if o["is_correct"] else 0)
                for i, o in enumerate(options)
            ],
        )
    return True


def db_count() -> int:
    with db_connect() as con:
        return con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


# ── Parsing ─────────────────────────────────────────────────

def clean_text(s: str) -> str:
    s = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", s)
    s = re.sub(r"[⬅\U0001f504➡️↩]", "", s)
    return s.strip()


# The bot may serve the test in English, Russian or Ukrainian — keep all three
# explanation markers. Non-ASCII strings are written as Unicode escapes so the
# source file stays ASCII-only.
EXPLANATION_PREFIXES = (
    "Explanation:",
    "\u041e\u0431\u044a\u044f\u0441\u043d\u0435\u043d\u0438\u0435:",  # ru
    "\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u043d\u044f:",  # uk
)


def parse_message(text: str) -> dict:
    result = {
        "question_num": None,
        "question_text": "",
        "options": [],
        "explanation": "",
        "raw_text": text or "",
    }
    if not text:
        return result

    lines = text.strip().split("\n")
    question_lines, options, explanation_lines = [], [], []
    in_explanation = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        matched_prefix = next((p for p in EXPLANATION_PREFIXES if line.startswith(p)), None)
        if matched_prefix or in_explanation:
            in_explanation = True
            part = line
            if matched_prefix:
                part = part[len(matched_prefix):]
            part = part.strip()
            # Drop counters like "1/5 allowed errors."
            part = re.sub(r"\d+/\d+.*?\.?", "", part).strip()
            if part:
                explanation_lines.append(part)
            continue

        if re.match(r"^\d+/\d+", line):
            continue

        if any(mark in line for mark in ("✅", "❌", "✔", "✖")):
            is_correct = "✅" in line or "✔" in line
            clean = clean_text(re.sub(r"[✅❌✔✖]", "", line))
            options.append({"text": clean, "is_correct": is_correct})
            continue

        if re.match(r"^\d+[)\.]", line) and question_lines:
            clean = clean_text(re.sub(r"^\d+[)\.]\s*", "", line))
            options.append({"text": clean, "is_correct": False})
            continue

        question_lines.append(clean_text(line))

    full_question = " ".join(question_lines).strip()
    num_match = re.match(r"^(\d+)[.\)]\s*(.*)", full_question)
    if num_match:
        result["question_num"] = int(num_match.group(1))
        result["question_text"] = num_match.group(2).strip()
    else:
        result["question_text"] = full_question

    result["options"] = options
    result["explanation"] = " ".join(explanation_lines).strip()
    return result


# ── Telegram ────────────────────────────────────────────────

async def wait_new_message(client, bot_entity, after_id, max_wait=15):
    for _ in range(max_wait * 2):
        async for msg in client.iter_messages(bot_entity, limit=10):
            if not msg.out and msg.id > after_id:
                return msg
        await asyncio.sleep(0.5)
    return None


# Lower-cased substrings that indicate a "Start test" button across locales.
START_BUTTON_KEYWORDS = (
    "start", "begin", "test", "quiz",
    "\u043d\u0430\u0447\u0430\u0442\u044c", "\u0442\u0435\u0441\u0442", "\u043f\u043e\u0447\u0430\u0442\u0438",  # ru/ru/uk
)

# Lower-cased substrings that indicate the bot has finished the test.
FINISHED_KEYWORDS = (
    "finished", "complete", "result",
    "\u043f\u043e\u0437\u0434\u0440\u0430\u0432\u043b\u044f", "\u0442\u0435\u0441\u0442 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d", "\u0442\u0435\u0441\u0442 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d", "\u043f\u0440\u0435\u0432\u044b\u0448\u0435\u043d\u0438", "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
)


async def collect_tickets():
    if API_ID == 0 or API_HASH == "":
        print("ERROR: API_ID / API_HASH are empty in credentials.py")
        return

    db_init()
    os.makedirs(IMAGES_DIR, exist_ok=True)

    seen_questions = db_load_seen()
    total_before = len(seen_questions)
    print(f"Database: {DB_FILE} ({total_before} questions already stored)")

    print("Connecting to Telegram...")
    async with TelegramClient("ca_driver_session", API_ID, API_HASH) as client:
        print("Connected.")

        bot_entity = await client.get_entity(BOT_USERNAME)
        print(f"Bot: {BOT_USERNAME}\n")

        last_id = 0
        async for msg in client.iter_messages(bot_entity, limit=1):
            last_id = msg.id

        async def start_test() -> bool:
            """Send /start and click the 'Start test' button. Returns True on success."""
            nonlocal last_id
            try:
                await client.send_message(bot_entity, "/start")
            except FloodWaitError as e:
                print(f"  FloodWait: sleeping {e.seconds}s...")
                await asyncio.sleep(e.seconds + 5)
                await client.send_message(bot_entity, "/start")
            menu_msg = await wait_new_message(client, bot_entity, after_id=last_id)
            if not menu_msg:
                return False
            last_id = menu_msg.id
            preview = repr(menu_msg.text[:60]) if menu_msg.text else "?"
            print(f"  [debug] Menu: {preview}")
            if menu_msg.buttons:
                for row in menu_msg.buttons:
                    for btn in row:
                        if any(k in btn.text.lower() for k in START_BUTTON_KEYWORDS):
                            print(f"  [debug] Clicking: [{btn.text}]")
                            await btn.click()
                            return True
            return False

        print("Sending /start ...")
        if not await start_test():
            print("ERROR: could not start the test.")
            return

        print("Collecting tickets...\n")

        new_count = 0
        skip_count = 0
        empty_rounds = 0  # consecutive restarts that produced no new questions

        while True:
            if LIMIT > 0 and new_count >= LIMIT:
                print(f"Reached the limit of {LIMIT} new questions for this session.")
                break

            cur_msg = await wait_new_message(client, bot_entity, after_id=last_id, max_wait=20)
            if not cur_msg:
                print("No new message from the bot — stopping.")
                break

            last_id = cur_msg.id

            if cur_msg.text and any(k in cur_msg.text.lower() for k in FINISHED_KEYWORDS):
                empty_rounds += 1
                if empty_rounds >= 5:
                    print(f"\nDone: {empty_rounds} rounds in a row produced no new questions.")
                    break
                print(f"\nTest finished, restarting (empty rounds: {empty_rounds}/5)...")
                await asyncio.sleep(DELAY)
                if not await start_test():
                    print("ERROR: could not restart the test.")
                    break
                continue

            # We only care about messages that have answer buttons.
            answer_btns = []
            if cur_msg.buttons:
                answer_btns = [
                    btn for row in cur_msg.buttons for btn in row
                    if "menu" not in btn.text.lower()
                    and "correction" not in btn.text.lower()
                ]
            if not answer_btns:
                print(f"  [debug] id={cur_msg.id} — not a question, skipping")
                continue

            parsed = parse_message(cur_msg.text)
            dedup_key = parsed["question_text"]

            # Duplicate — advance to the next question without saving.
            if dedup_key in seen_questions:
                skip_count += 1
                print(f"  [skip] {repr(dedup_key[:55])}")
                await answer_btns[0].click()
                await asyncio.sleep(DELAY)
                continue

            # Download the attached image, if any.
            image_path = None
            if cur_msg.media and isinstance(cur_msg.media, MessageMediaPhoto):
                img_filename = f"{IMAGES_DIR}/q_{total_before + new_count + 1:03d}.jpg"
                await client.download_media(cur_msg.media, img_filename)
                image_path = img_filename

            # Click the first answer so the bot reveals the result.
            await answer_btns[0].click()
            await asyncio.sleep(DELAY)

            # Re-read the message — the bot has now appended ✅/❌ and the explanation.
            result_msg = await client.get_messages(bot_entity, ids=cur_msg.id)
            if result_msg and result_msg.text:
                parsed_result = parse_message(result_msg.text)
                if parsed_result["options"]:
                    parsed["options"] = parsed_result["options"]
                if parsed_result["explanation"]:
                    parsed["explanation"] = parsed_result["explanation"]

            is_new = db_save_ticket(parsed, parsed["options"], image_path)
            if is_new:
                seen_questions.add(dedup_key)
                new_count += 1
                empty_rounds = 0
                q_display = dedup_key[:65] + "..." if len(dedup_key) > 65 else dedup_key
                print(f"  [{total_before + new_count:03d}] {q_display}")

    total_after = db_count()
    print(
        f"\nTotal in database: {total_after} questions "
        f"(+{new_count} new, {skip_count} duplicates skipped)"
    )


if __name__ == "__main__":
    asyncio.run(collect_tickets())
