# AI Typing Trainer

A CLI typing trainer with multiple practice modes.

## Modules

- **Word Trainer** — themed word sets with speed and accuracy stats
- **Chat Trainer** — Reading Speed, Quick Responses, and AI Dialog modes
- **Multiplication** — multiplication table drill with per-cell timing
- **Listening** — dictation (planned)
- **Motivation** — points, leaderboard, achievements (planned)

## Requirements

- Python 3.10+
- Optional: [WezTerm](https://wezfurlong.org/wezterm/) for the `run.bat` / `run.sh` launchers

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
```

## Run

```bash
python ai_typing_trainer/src/main.py
```

Or use the launcher scripts in `ai_typing_trainer/`:

```bash
./ai_typing_trainer/run.sh     # Linux / macOS
ai_typing_trainer\run.bat      # Windows
```

## Project layout

```
ai_typing_trainer/
  data/         # word lists, chat content, UI translations
  src/          # application code
    modules/    # individual trainer modules
  run.sh        # WezTerm launcher (Unix)
  run.bat       # WezTerm launcher (Windows)
```
