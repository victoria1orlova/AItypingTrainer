# Traffic Rules — Canadian Driving Ticket Collector

A tooling kit that builds a local database of Canadian Class 7 driving-test
tickets by walking the public Telegram bot [@ca_driver_bot](https://t.me/ca_driver_bot).
The resulting `tickets.db` powers the Traffic Rules study module of the parent
`ai_typing_trainer` project, and can also be browsed in any modern browser via
the bundled HTML viewer.

> `tickets.db` and `ticket_images/` are **not** committed to the repository —
> they are produced locally by running the collector script described below.

---

## How it works

`@ca_driver_bot` serves study tickets for the Canadian driving exam: each
ticket is a question with four options, one correct answer, an explanation,
and occasionally a clarifying image.

The collector logs in to Telegram as your own user, automatically picks an
answer for every question and reads the result the bot sends back. The
question, options, correct answer, explanation and image are saved to a local
SQLite database. The script keeps restarting the test until two full rounds
pass without producing any new question, at which point the catalogue is
considered complete.

### What gets captured

- Question text
- All answer options, with the correct one flagged
- Explanation
- Image (when the question has one)

### Outputs

| File              | Contents                                |
| ----------------- | --------------------------------------- |
| `tickets.db`      | SQLite database with every ticket       |
| `ticket_images/`  | JPEGs referenced by questions           |
| `viewer.html`     | Browser viewer (open it directly)       |

---

## Setup

### 1. Python

Python 3.10 or newer. On Windows make sure **Add Python to PATH** is checked
during installation.

### 2. Install dependencies

```bash
pip install telethon
```

### 3. Telegram API credentials

The script logs in as a Telegram client, so it needs your personal API id
and hash:

1. Open [my.telegram.org](https://my.telegram.org) and sign in with your
   phone number.
2. Go to **API development tools** and create an application (name and
   platform are arbitrary).
3. Copy `App api_id` (a number) and `App api_hash` (a string).

### 4. Drop the credentials into a local file

```bash
cp credentials.py.example credentials.py
```

Then edit `credentials.py`:

```python
API_ID = 12345678              # your api_id
API_HASH = "abcdef1234..."     # your api_hash
```

`credentials.py` is in `.gitignore` — it will never be committed.

---

## Usage

### Run the collector

```bash
python ca_driver_bot_collector.py
```

The first run will prompt for your phone number and a one-time confirmation
code from Telegram. After that a session file `ca_driver_session.session`
is created and subsequent runs reuse it.

The collector will:

- Click **Start test** in the bot's main menu.
- Answer each question and read back the result.
- Restart the test when it ends.
- Stop once five rounds in a row produce no new questions.

Console output looks like this:

```
Database: tickets.db (41 questions already stored)
  [042] What is the speed limit required when ...
  [skip] 'What does this road sign mean?'
Test finished, restarting (empty rounds: 1/5)...
Done: 5 rounds in a row produced no new questions.
```

### Browse tickets in a browser

Open `viewer.html` directly in your browser, click **Load tickets.db** and
pick the file. The viewer shows a searchable list on the left and the
full question, options, explanation and image on the right.

> An internet connection is needed once to fetch `sql.js` from a CDN.

---

## Development

### Stack

| Component         | Technology |
| ----------------- | ---------- |
| Telegram client   | [Telethon](https://github.com/LonamiWebs/Telethon) |
| Database          | SQLite (Python stdlib) |
| Viewer            | Vanilla HTML/CSS/JS + [sql.js](https://github.com/sql-js/sql.js) |

### Layout

```
TrafficRules/
├── ca_driver_bot_collector.py   # collector
├── debug_bot.py                 # diagnostic helper
├── credentials.py.example       # template for API credentials
├── credentials.py               # local credentials (gitignored)
├── viewer.html                  # browser viewer
├── tickets.db                   # SQLite database
└── ticket_images/               # downloaded images
```

### Schema

```sql
tickets (
    id            INTEGER PRIMARY KEY,
    question_num  INTEGER,
    question_text TEXT UNIQUE,   -- deduplication key
    explanation   TEXT,
    has_image     INTEGER,
    image_path    TEXT,
    raw_text      TEXT
)

options (
    id         INTEGER PRIMARY KEY,
    ticket_id  INTEGER → tickets.id,
    position   INTEGER,
    text       TEXT,
    is_correct INTEGER
)
```

### Settings

All knobs live at the top of `ca_driver_bot_collector.py`:

| Setting       | Default          | Description |
| ------------- | ---------------- | ----------- |
| `DELAY`       | `2.0`            | Pause between bot requests (seconds). Keep this above 1.5. |
| `LIMIT`       | `500`            | Maximum new questions per session (0 disables the cap). |
| `IMAGES_DIR`  | `ticket_images`  | Where downloaded images are stored. |
| `DB_FILE`     | `tickets.db`     | SQLite database file. |
