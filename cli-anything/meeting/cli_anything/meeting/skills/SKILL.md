# Meeting Assistant CLI — SKILL.md

## Overview

**cli-anything-meeting** is a command-line Meeting Assistant that records, transcribes,
translates, and summarizes meetings entirely locally using
[Gemma 4 E2B/E4B](https://ollama.com/library/gemma4) (audio-capable) through
[Ollama](https://ollama.com/).  No cloud services required.

---

## Prerequisites

| Requirement | Install |
|---|---|
| Python 3.10+ | https://python.org |
| Ollama | https://ollama.com/download |
| Gemma 4 audio model | `ollama pull gemma4:e4b` |
| ffmpeg (recommended) | `brew install ffmpeg` / `sudo apt install ffmpeg` |

### Optional (sounddevice fallback for recording)
```bash
pip install cli-anything-meeting[audio]
```

---

## Installation

```bash
cd /path/to/meeting/
pip install -e .

# Verify
cli-anything-meeting --version
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `--host` | `http://localhost:11434` | Ollama server URL |
| `--model` | `gemma4:e4b` | Ollama model (must be audio-capable for transcription) |
| `--json` | off | Output all results as JSON |

---

## Commands Reference

### Global flags

```
cli-anything-meeting [--json] [--model MODEL] [--host URL] COMMAND
```

---

### `record` — Microphone recording

#### `record start`
Record audio from the default microphone.

```bash
# Record for 60 seconds (default)
cli-anything-meeting record start

# Record for 5 minutes, save to specific file
cli-anything-meeting record start --duration 300 --output standup.wav
```

Options:
- `--duration / -d` — Recording length in seconds (default: 60)
- `--output / -o` — Output file path (default: `~/meeting_minutes/recordings/recording_<timestamp>.wav`)

#### `record list`
List recorded audio files.

```bash
cli-anything-meeting record list
cli-anything-meeting record list --dir /custom/path
```

---

### `transcribe` — Audio-to-text

#### `transcribe audio`
Transcribe an existing audio file.

```bash
cli-anything-meeting transcribe audio meeting.wav
cli-anything-meeting transcribe audio meeting.wav --lang en
cli-anything-meeting transcribe audio meeting.wav --output transcript.txt
```

Options:
- `--lang / -l` — Spoken language (BCP-47 or name, default: `th`)
- `--output / -o` — Save transcription to file

#### `transcribe live`
Record and immediately transcribe (single command).

```bash
cli-anything-meeting transcribe live --duration 120
cli-anything-meeting transcribe live --duration 30 --lang en --output result.txt
```

Options:
- `--duration / -d` — Recording length in seconds (default: 60)
- `--lang / -l` — Spoken language (default: `th`)
- `--output / -o` — Save transcription to file

---

### `translate` — Language translation

#### `translate text`
Translate text from argument or stdin.

```bash
cli-anything-meeting translate text "Hello, world" --to-lang th
echo "Good morning" | cli-anything-meeting translate text --from-lang en --to-lang th
```

Options:
- `--from-lang` — Source language (`auto` to detect, default: `auto`)
- `--to-lang` — Target language (default: `th`)
- `--output / -o` — Save result to file

#### `translate file`
Translate a text file.

```bash
cli-anything-meeting translate file transcript.txt --to-lang th
cli-anything-meeting translate file notes.txt --from-lang en --to-lang th --output notes_th.txt
```

Options:
- `--from-lang` — Source language (default: `auto`)
- `--to-lang` — Target language (default: `th`)
- `--output / -o` — Output file (default: `<input>.<to_lang>.txt`)

---

### `summarize` — Content summarization

#### `summarize text`
Summarize text from argument or stdin (output in Thai).

```bash
cli-anything-meeting summarize text "The team agreed to ship feature X by Friday…"
cat transcript.txt | cli-anything-meeting summarize text --style action-items
```

#### `summarize file`
Summarize a text file.

```bash
cli-anything-meeting summarize file transcript.txt
cli-anything-meeting summarize file notes.txt --style paragraph --output summary.txt
```

#### `summarize meeting` ★ Full Pipeline

The primary command — executes the complete meeting pipeline:

```
1. Record audio from microphone (or accept --file)
2. Transcribe via Gemma 4 audio model
3. Translate to Thai (or --translate-to language) if needed
4. Summarize with chosen style
5. Save as markdown minutes file
```

```bash
# 5-minute meeting → Thai bullet-point minutes
cli-anything-meeting summarize meeting --duration 300

# Use existing recording, English speech, translate to Thai, action items
cli-anything-meeting summarize meeting \
  --file standup.wav \
  --lang en \
  --style action-items \
  --title "Daily Standup 2024-01-05"

# 2-minute test with custom output path
cli-anything-meeting summarize meeting \
  --duration 120 \
  --lang th \
  --style bullet \
  --output ~/Desktop/todays_meeting.md
```

Options:
| Option | Default | Description |
|---|---|---|
| `--file / -f` | — | Use existing audio file instead of recording |
| `--duration / -d` | 60 | Recording duration in seconds |
| `--lang / -l` | `th` | Spoken language in the audio |
| `--translate-to` | `th` | Translate transcript to this language |
| `--style` | `bullet` | `bullet` / `paragraph` / `action-items` |
| `--title` | auto | Meeting title for the minutes header |
| `--output / -o` | auto | Minutes output file path |
| `--keep-audio` | off | Keep the temp recording file |

Summary styles:
- `bullet` — Bullet-point summary of key points and decisions
- `paragraph` — Flowing prose summary
- `action-items` — Checklist of tasks with owners and deadlines

---

### `minutes` — Minutes file management

#### `minutes save`
Save text as a structured markdown minutes file.

```bash
cat summary.txt | cli-anything-meeting minutes save --title "Q1 Planning"
cli-anything-meeting minutes save "Action: Fix login bug" --title "Bug Triage"
```

Options:
- `--title / -t` — Meeting title
- `--output / -o` — Output path (default: `~/meeting_minutes/<title>_<timestamp>.md`)

#### `minutes list`
List all saved minutes files.

```bash
cli-anything-meeting minutes list
cli-anything-meeting minutes list --limit 5
```

#### `minutes view`
View a minutes file.

```bash
cli-anything-meeting minutes view meeting_20240105_143000.md
cli-anything-meeting minutes view --index 1   # most recent
```

---

### `repl` — Interactive mode

Launch an interactive REPL session where commands can be typed without the
`cli-anything-meeting` prefix.

```bash
cli-anything-meeting repl
```

```
Meeting Assistant REPL
Model: gemma4:e4b  |  Host: http://localhost:11434
Type 'help' for commands, 'exit' to quit.

meeting> transcribe audio meeting.wav
meeting> summarize meeting --duration 60
meeting> minutes list
meeting> exit
```

---

## JSON output mode

Add `--json` to any command for machine-readable output:

```bash
cli-anything-meeting --json transcribe audio meeting.wav
# → {"text": "เนื้อหาการประชุม..."}

cli-anything-meeting --json summarize meeting --duration 60
# → {"ok": true, "minutes_file": "...", "transcript": "...", "summary": "...", ...}
```

---

## Audio Recording Details

**Primary (recommended):** ffmpeg via subprocess

| Platform | Input device |
|---|---|
| macOS | `-f avfoundation -i :0` |
| Linux | `-f alsa -i default` |
| Windows | `-f dshow` DirectShow audio |

**Fallback:** sounddevice + numpy
Install with: `pip install cli-anything-meeting[audio]`

**macOS microphone permission:**
Go to System Settings → Privacy & Security → Microphone → enable Terminal.

---

## Minutes File Format

Minutes are saved as Markdown with a YAML front-matter header:

```markdown
---
date: 2024-01-05
time: 14:30
title: "Daily Standup"
model: "gemma4:e4b"
lang: "th"
style: "bullet"
---

# Daily Standup

## บทสรุปการประชุม

- ทีมได้ทบทวนสถานะงาน Sprint 12
- ...

## คำบันทึกถ้อยคำ (Transcript)

...
```

Default location: `~/meeting_minutes/`

---

## Gemma 4 Audio Model

The tool uses `gemma4:e4b` (4B parameter, audio-capable) by default.
You may also use `gemma4:e2b` for a smaller/faster model.

```bash
# Pull the model first
ollama pull gemma4:e4b

# Use the smaller variant
cli-anything-meeting --model gemma4:e2b summarize meeting --duration 60
```

The model receives base64-encoded audio data directly via Ollama's multimodal
`/api/generate` endpoint, so no separate transcription service is needed.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot connect to Ollama` | Run `ollama serve` first |
| `ffmpeg not found` | `brew install ffmpeg` or `sudo apt install ffmpeg` |
| `Recording failed (avfoundation)` | Grant microphone access to Terminal in macOS Privacy settings |
| `Model not found` | `ollama pull gemma4:e4b` |
| Empty transcription | Check audio quality; try a longer recording or closer microphone |

---

## Architecture

```
cli_anything/meeting/
├── __init__.py
├── __main__.py          # python -m cli_anything.meeting
├── meeting_cli.py       # Click CLI (commands, groups, REPL)
├── utils/
│   ├── __init__.py
│   └── meeting_backend.py   # record, transcribe, translate, summarize, save
├── core/
│   └── __init__.py
└── skills/
    └── SKILL.md         # this file
```
