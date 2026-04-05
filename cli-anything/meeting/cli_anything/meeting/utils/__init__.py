"""Utility modules for cli-anything-meeting."""
from cli_anything.meeting.utils.meeting_backend import (
    OLLAMA_URL,
    DEFAULT_MODEL,
    record_audio,
    transcribe,
    translate,
    summarize,
    save_minutes,
)

__all__ = [
    "OLLAMA_URL",
    "DEFAULT_MODEL",
    "record_audio",
    "transcribe",
    "translate",
    "summarize",
    "save_minutes",
]
