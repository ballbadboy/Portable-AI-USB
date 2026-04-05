"""
meeting_backend.py
==================
Core backend for Meeting Assistant CLI.

Provides:
  - Audio recording via ffmpeg subprocess (primary, cross-platform)
    with sounddevice fallback when available
  - Transcription via Gemma 4 audio model through Ollama API
  - Translation via Ollama
  - Summarization via Ollama
  - Meeting minutes file I/O
"""

from __future__ import annotations

import base64
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_URL: str = "http://localhost:11434"
DEFAULT_MODEL: str = "gemma4:e4b"

# Directory where minutes are stored by default
MINUTES_DIR: Path = Path.home() / "meeting_minutes"

# Timeout for Ollama API calls (seconds)
OLLAMA_TIMEOUT: int = 300


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_ffmpeg() -> str:
    """Return ffmpeg executable path or raise RuntimeError with install hint."""
    for candidate in ("ffmpeg", "ffmpeg.exe"):
        try:
            result = subprocess.run(
                [candidate, "-version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError(
        "ffmpeg is not installed or not in PATH.\n"
        "  macOS:   brew install ffmpeg\n"
        "  Ubuntu:  sudo apt install ffmpeg\n"
        "  Windows: https://ffmpeg.org/download.html\n"
        "Alternatively, install the optional audio extras:\n"
        "  pip install cli-anything-meeting[audio]"
    )


def _ffmpeg_input_args() -> list[str]:
    """Return platform-appropriate ffmpeg input arguments for microphone capture."""
    system = platform.system()
    if system == "Darwin":
        # macOS – AVFoundation; ':0' is usually the default input device
        return ["-f", "avfoundation", "-i", ":0"]
    elif system == "Windows":
        # Windows – DirectShow; first audio device
        return ["-f", "dshow", "-i", "audio=@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\wave_{00000000-0000-0000-0000-000000000000}"]
    else:
        # Linux – ALSA default
        return ["-f", "alsa", "-i", "default"]


def _record_with_sounddevice(duration_sec: int, output_path: str) -> None:
    """Fallback recorder using sounddevice + numpy (optional dependency)."""
    try:
        import sounddevice as sd  # type: ignore
        import numpy as np  # type: ignore
        import wave
    except ImportError as exc:
        raise RuntimeError(
            "sounddevice/numpy not installed. "
            "Install extras: pip install cli-anything-meeting[audio]"
        ) from exc

    sample_rate = 16000
    print(f"Recording {duration_sec}s at {sample_rate}Hz via sounddevice …", file=sys.stderr)
    audio = sd.rec(
        int(duration_sec * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


def _ollama_generate(
    prompt: str,
    model: str,
    images: Optional[list[str]] = None,
    host: str = OLLAMA_URL,
) -> str:
    """
    Call the Ollama /api/generate endpoint.

    Args:
        prompt:  Text prompt.
        model:   Model name, e.g. "gemma4:e4b".
        images:  Optional list of base64-encoded binary blobs (audio or image).
        host:    Ollama base URL.

    Returns:
        The complete model response as a string.

    Raises:
        requests.HTTPError: On non-2xx response.
        requests.ConnectionError: When Ollama is not reachable.
    """
    url = f"{host.rstrip('/')}/api/generate"
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if images:
        payload["images"] = images

    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
    except requests.ConnectionError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {host}.\n"
            "Make sure Ollama is running:  ollama serve"
        ) from exc

    data = resp.json()
    return data.get("response", "").strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_audio(
    duration_sec: int,
    output_path: str,
    *,
    host: str = OLLAMA_URL,  # unused here but kept for API symmetry
) -> str:
    """
    Record microphone audio for *duration_sec* seconds and save to *output_path*.

    Uses ffmpeg as the primary recorder (most portable across macOS/Linux/Windows).
    Falls back to sounddevice when ffmpeg is unavailable but sounddevice is installed.

    Args:
        duration_sec: Recording duration in seconds.
        output_path:  Destination file path (wav/mp3/m4a – determined by extension).

    Returns:
        Absolute path to the recorded file.

    Raises:
        RuntimeError: When neither ffmpeg nor sounddevice is available.
    """
    output_path = str(Path(output_path).expanduser().resolve())
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        ffmpeg = _check_ffmpeg()
        input_args = _ffmpeg_input_args()
        cmd = [
            ffmpeg,
            "-y",                    # overwrite without asking
            *input_args,
            "-t", str(duration_sec), # duration
            "-ar", "16000",          # 16 kHz sample rate (good for speech)
            "-ac", "1",              # mono
            output_path,
        ]
        print(f"Recording {duration_sec}s via ffmpeg → {output_path}", file=sys.stderr)
        result = subprocess.run(cmd, capture_output=True, timeout=duration_sec + 30)
        if result.returncode != 0:
            stderr_msg = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ffmpeg exited with code {result.returncode}.\n{stderr_msg}\n\n"
                "Tip (macOS): Grant terminal microphone access in\n"
                "  System Settings → Privacy & Security → Microphone"
            )
    except RuntimeError as ffmpeg_error:
        # Try sounddevice fallback
        if "not installed" in str(ffmpeg_error) or "not in PATH" in str(ffmpeg_error):
            print(
                "ffmpeg not found – trying sounddevice fallback …",
                file=sys.stderr,
            )
            _record_with_sounddevice(duration_sec, output_path)
        else:
            raise

    return output_path


def transcribe(
    audio_path: str,
    model: str = DEFAULT_MODEL,
    language: str = "th",
    *,
    host: str = OLLAMA_URL,
) -> str:
    """
    Transcribe an audio file to text using the Gemma 4 audio model via Ollama.

    The audio file is read, base64-encoded, and sent to the model as a multimodal
    input alongside a transcription prompt.

    Args:
        audio_path: Path to the audio file (wav, mp3, m4a, ogg, …).
        model:      Ollama model name (must be audio-capable, e.g. gemma4:e4b).
        language:   Expected spoken language as BCP-47 or natural name (default: "th").
        host:       Ollama base URL.

    Returns:
        Transcribed text string.

    Raises:
        FileNotFoundError: When the audio file does not exist.
        RuntimeError:      On Ollama connection or model errors.
    """
    audio_path = str(Path(audio_path).expanduser().resolve())
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    with open(audio_path, "rb") as fh:
        audio_b64 = base64.b64encode(fh.read()).decode("utf-8")

    lang_label = "Thai" if language in ("th", "thai", "ไทย") else language

    prompt = (
        f"Please transcribe the following audio recording accurately. "
        f"The spoken language is {lang_label}. "
        f"Output only the transcription text with no commentary or labels."
    )

    return _ollama_generate(prompt, model, images=[audio_b64], host=host)


def translate(
    text: str,
    source_lang: str,
    target_lang: str,
    model: str = DEFAULT_MODEL,
    *,
    host: str = OLLAMA_URL,
) -> str:
    """
    Translate *text* from *source_lang* to *target_lang* using Ollama.

    Args:
        text:        Source text to translate.
        source_lang: Source language name or code (e.g. "en", "English", "auto").
        target_lang: Target language name or code (e.g. "th", "Thai").
        model:       Ollama model name.
        host:        Ollama base URL.

    Returns:
        Translated text string.
    """
    if not text.strip():
        return text

    if source_lang.lower() in ("auto", "detect", ""):
        source_desc = "the source language (detect automatically)"
    else:
        source_desc = source_lang

    target_label = "Thai" if target_lang in ("th", "thai", "ไทย") else target_lang

    prompt = (
        f"Translate the following text from {source_desc} to {target_label}. "
        f"Output only the translation with no explanations or labels.\n\n"
        f"Text to translate:\n{text}"
    )

    return _ollama_generate(prompt, model, host=host)


def summarize(
    text: str,
    model: str = DEFAULT_MODEL,
    style: str = "bullet",
    *,
    host: str = OLLAMA_URL,
) -> str:
    """
    Summarize meeting *text* in Thai using Ollama.

    Args:
        text:  Meeting transcript or notes to summarize.
        model: Ollama model name.
        style: Output style – one of:
                 "bullet"       → bullet-point summary
                 "paragraph"    → prose summary
                 "action-items" → action items only with owners and deadlines
        host:  Ollama base URL.

    Returns:
        Summary string (in Thai).
    """
    if not text.strip():
        return text

    style_instructions = {
        "bullet": (
            "สรุปเนื้อหาการประชุมในรูปแบบหัวข้อย่อย (bullet points) เป็นภาษาไทย "
            "ครอบคลุมประเด็นหลัก ข้อตกลง และสิ่งที่ต้องดำเนินการต่อ"
        ),
        "paragraph": (
            "สรุปเนื้อหาการประชุมในรูปแบบย่อหน้า (paragraphs) เป็นภาษาไทย "
            "อธิบายบริบท ประเด็นที่พูดถึง และผลสรุปของการประชุม"
        ),
        "action-items": (
            "สกัดเฉพาะ Action Items จากการประชุม เป็นภาษาไทย "
            "โดยระบุ: งานที่ต้องทำ, ผู้รับผิดชอบ (ถ้ามี), กำหนดเวลา (ถ้ามี) "
            "ในรูปแบบ checklist"
        ),
    }

    instruction = style_instructions.get(
        style,
        style_instructions["bullet"],
    )

    prompt = (
        f"{instruction}\n\n"
        f"เนื้อหาการประชุม:\n{text}"
    )

    return _ollama_generate(prompt, model, host=host)


def save_minutes(
    text: str,
    output_path: str,
    *,
    title: str = "",
    metadata: Optional[dict] = None,
) -> str:
    """
    Save meeting minutes to a Markdown file.

    Creates parent directories as needed. Adds a YAML-style header block
    with date, title, and any extra metadata.

    Args:
        text:        Meeting minutes content (plain text or Markdown).
        output_path: Destination file path (will be created/overwritten).
        title:       Optional meeting title for the header.
        metadata:    Optional dict of extra fields to include in the header.

    Returns:
        Absolute path of the saved file.
    """
    output_path = str(Path(output_path).expanduser().resolve())
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    header_lines = [
        "---",
        f"date: {date_str}",
        f"time: {time_str}",
    ]
    if title:
        header_lines.append(f"title: \"{title}\"")
    if metadata:
        for key, value in metadata.items():
            header_lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    header_lines.append("---")
    header_lines.append("")

    if title:
        header_lines.append(f"# {title}")
    else:
        header_lines.append(f"# รายงานการประชุม – {date_str} {time_str}")
    header_lines.append("")

    full_content = "\n".join(header_lines) + text + "\n"

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(full_content)

    return output_path
