"""
meeting_cli.py
==============
Full Click CLI for Meeting Assistant.

Entry point: cli-anything-meeting

Groups & commands
-----------------
record
  start       Record audio from microphone
  stop        (stub) Stop a background recording session
  list        List recorded audio files

transcribe
  audio       Transcribe an audio file to text
  live        Record audio then immediately transcribe

translate
  text        Translate text from stdin or argument
  file        Translate a text file

summarize
  text        Summarize text from stdin or argument
  file        Summarize a text file
  meeting     Full pipeline: record→transcribe→translate→summarize→save

minutes
  save        Save text as a markdown minutes file
  list        List saved minutes files
  view        View a minutes file

repl          Interactive REPL mode
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

from cli_anything.meeting.utils.meeting_backend import (
    DEFAULT_MODEL,
    MINUTES_DIR,
    OLLAMA_URL,
    record_audio,
    save_minutes,
    summarize,
    transcribe,
    translate,
)

# ---------------------------------------------------------------------------
# Shared state passed via Click context
# ---------------------------------------------------------------------------

class AppContext:
    def __init__(self, model: str, host: str, output_json: bool):
        self.model = model
        self.host = host
        self.output_json = output_json


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_result(ctx_obj: AppContext, data: dict) -> None:
    """Print result as JSON or human-readable based on --json flag."""
    if ctx_obj.output_json:
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for key, value in data.items():
            if key == "text" or key == "result" or key == "summary":
                click.echo(value)
            elif key not in ("ok",):
                click.secho(f"{key}: {value}", fg="cyan", err=True)


def _error(ctx_obj: AppContext, message: str, exc: Optional[Exception] = None) -> None:
    if ctx_obj.output_json:
        payload = {"error": message}
        if exc:
            payload["detail"] = str(exc)
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        click.secho(f"Error: {message}", fg="red", err=True)
        if exc:
            click.secho(f"  {exc}", fg="yellow", err=True)


# ---------------------------------------------------------------------------
# Root command group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--json", "output_json", is_flag=True, default=False,
              help="Output results as JSON.")
@click.option("--model", default=DEFAULT_MODEL, show_default=True,
              help="Ollama model to use (must support audio for transcription).")
@click.option("--host", default=OLLAMA_URL, show_default=True,
              help="Ollama server URL.")
@click.version_option("1.0.0", prog_name="cli-anything-meeting")
@click.pass_context
def cli(ctx: click.Context, output_json: bool, model: str, host: str) -> None:
    """
    Meeting Assistant CLI powered by Gemma 4 via Ollama.

    Record meetings, transcribe audio, translate and summarize content,
    and save professional meeting minutes — all from the command line.

    \b
    Quick start (full pipeline):
      cli-anything-meeting summarize meeting --duration 60

    \b
    Transcribe an existing file:
      cli-anything-meeting transcribe audio meeting.wav

    \b
    Interactive mode:
      cli-anything-meeting repl
    """
    ctx.ensure_object(dict)
    ctx.obj = AppContext(model=model, host=host, output_json=output_json)


# ===========================================================================
# Group: record
# ===========================================================================

@cli.group()
@click.pass_obj
def record(obj: AppContext) -> None:
    """Record audio from the microphone."""


@record.command("start")
@click.option("--duration", "-d", default=60, show_default=True,
              help="Recording duration in seconds.")
@click.option("--output", "-o", default="", help="Output file path (default: auto-generated).")
@click.pass_obj
def record_start(obj: AppContext, duration: int, output: str) -> None:
    """Start recording audio from the default microphone.

    The recording lasts for --duration seconds.  When --output is omitted,
    a timestamped file is created under ~/meeting_minutes/recordings/.
    """
    if not output:
        recordings_dir = MINUTES_DIR / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = str(recordings_dir / f"recording_{ts}.wav")

    click.secho(f"Recording for {duration}s …  (Ctrl+C to cancel)", fg="yellow", err=True)
    try:
        saved = record_audio(duration, output, host=obj.host)
        _print_result(obj, {"ok": True, "file": saved, "duration_sec": duration})
    except RuntimeError as exc:
        _error(obj, "Recording failed.", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        click.secho("\nRecording cancelled.", fg="red", err=True)
        sys.exit(130)


@record.command("stop")
@click.pass_obj
def record_stop(obj: AppContext) -> None:
    """Stop an active background recording session (not yet implemented)."""
    click.secho(
        "Background recording is not yet implemented.\n"
        "Use `record start --duration <seconds>` for a timed recording.",
        fg="yellow",
        err=True,
    )


@record.command("list")
@click.option("--dir", "recordings_dir", default="",
              help="Directory to list (default: ~/meeting_minutes/recordings/).")
@click.pass_obj
def record_list(obj: AppContext, recordings_dir: str) -> None:
    """List recorded audio files."""
    if not recordings_dir:
        recordings_dir = str(MINUTES_DIR / "recordings")

    search_dir = Path(recordings_dir).expanduser()
    if not search_dir.exists():
        click.secho(f"No recordings directory found at {search_dir}", fg="yellow", err=True)
        if obj.output_json:
            click.echo(json.dumps({"files": []}, indent=2))
        return

    audio_exts = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}
    files = sorted(
        [f for f in search_dir.iterdir() if f.suffix.lower() in audio_exts],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if obj.output_json:
        click.echo(json.dumps({"files": [str(f) for f in files]}, indent=2))
    else:
        if not files:
            click.secho("No recordings found.", fg="yellow")
        for f in files:
            size_kb = f.stat().st_size // 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            click.echo(f"  {mtime}  {size_kb:>6}KB  {f.name}")


# ===========================================================================
# Group: transcribe
# ===========================================================================

@cli.group()
@click.pass_obj
def transcribe_group(obj: AppContext) -> None:
    """Transcribe audio to text using Gemma 4 audio model."""


# Re-register with the correct group name
cli.add_command(transcribe_group, name="transcribe")


@transcribe_group.command("audio")
@click.argument("audio_file", type=click.Path(exists=True, readable=True))
@click.option("--lang", "-l", default="th", show_default=True,
              help="Spoken language in the audio (BCP-47 or name).")
@click.option("--output", "-o", default="", help="Save transcription to this file.")
@click.pass_obj
def transcribe_audio(obj: AppContext, audio_file: str, lang: str, output: str) -> None:
    """Transcribe AUDIO_FILE to text.

    \b
    Examples:
      cli-anything-meeting transcribe audio meeting.wav
      cli-anything-meeting transcribe audio meeting.wav --lang en
      cli-anything-meeting transcribe audio meeting.wav --output transcript.txt
    """
    click.secho(f"Transcribing {audio_file} …", fg="cyan", err=True)
    try:
        result = transcribe(audio_file, model=obj.model, language=lang, host=obj.host)
    except (FileNotFoundError, RuntimeError) as exc:
        _error(obj, "Transcription failed.", exc)
        sys.exit(1)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.secho(f"Transcription saved to {output}", fg="green", err=True)

    _print_result(obj, {"text": result})


@transcribe_group.command("live")
@click.option("--duration", "-d", default=60, show_default=True,
              help="Recording duration in seconds.")
@click.option("--lang", "-l", default="th", show_default=True,
              help="Spoken language in the audio.")
@click.option("--output", "-o", default="", help="Save transcription to this file.")
@click.pass_obj
def transcribe_live(obj: AppContext, duration: int, lang: str, output: str) -> None:
    """Record audio from the microphone then immediately transcribe it.

    \b
    Examples:
      cli-anything-meeting transcribe live --duration 120
      cli-anything-meeting transcribe live --duration 30 --lang en
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        click.secho(f"Recording {duration}s …  (Ctrl+C to cancel)", fg="yellow", err=True)
        record_audio(duration, tmp_path, host=obj.host)

        click.secho("Transcribing …", fg="cyan", err=True)
        result = transcribe(tmp_path, model=obj.model, language=lang, host=obj.host)
    except (RuntimeError, FileNotFoundError) as exc:
        _error(obj, "Live transcription failed.", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        click.secho("\nCancelled.", fg="red", err=True)
        sys.exit(130)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.secho(f"Transcription saved to {output}", fg="green", err=True)

    _print_result(obj, {"text": result})


@transcribe_group.command("realtime")
@click.option("--chunk", "-c", default=10, show_default=True,
              help="Chunk size in seconds per transcription call.")
@click.option("--lang", "-l", default="th", show_default=True,
              help="Spoken language.")
@click.option("--output", "-o", default="", help="Save full transcript to file.")
@click.option("--translate-to", default="", help="Translate each chunk to this language (e.g. th, en).")
@click.option("--summarize", "do_summarize", is_flag=True, default=False,
              help="Print running summary every 5 chunks.")
@click.pass_obj
def transcribe_realtime(obj: AppContext, chunk: int, lang: str, output: str,
                        translate_to: str, do_summarize: bool) -> None:
    """Real-time transcription: record in chunks, show text immediately.

    Records audio in short chunks and transcribes each one instantly via
    Gemma 4 — so you see the transcript growing in real-time. Press Ctrl+C
    to stop and optionally save the full transcript.

    \b
    Examples:
      cli-anything-meeting transcribe realtime
      cli-anything-meeting transcribe realtime --chunk 5 --lang en --translate-to th
      cli-anything-meeting transcribe realtime --output minutes.txt --summarize
    """
    import signal

    all_text: list[str] = []
    chunk_count = 0
    stop_flag = False

    def _handle_sig(sig, frame):  # noqa: ANN001
        nonlocal stop_flag
        stop_flag = True

    signal.signal(signal.SIGINT, _handle_sig)

    click.secho("\n🎙️  Real-time transcription started", fg="green", bold=True)
    click.secho(f"   Chunk: {chunk}s | Lang: {lang} | Ctrl+C to stop\n", fg="yellow")
    click.secho("─" * 60, fg="blue")

    try:
        while not stop_flag:
            chunk_count += 1
            tmp_path = tempfile.mktemp(suffix=".wav")
            try:
                # Record one chunk silently
                record_audio(chunk, tmp_path, host=obj.host)
                if stop_flag:
                    break

                # Transcribe chunk
                text = transcribe(tmp_path, model=obj.model, language=lang, host=obj.host).strip()
                if not text:
                    continue

                # Optionally translate
                if translate_to and translate_to != lang:
                    text = translate(text, source_lang=lang, target_lang=translate_to,
                                     model=obj.model, host=obj.host).strip()

                all_text.append(text)

                # Print real-time output
                ts = datetime.now().strftime("%H:%M:%S")
                click.secho(f"[{ts}] ", fg="cyan", nl=False)
                click.echo(text)

                # Running summary every 5 chunks
                if do_summarize and chunk_count % 5 == 0 and all_text:
                    combined = " ".join(all_text)
                    click.secho("\n── สรุปชั่วคราว ──", fg="magenta", bold=True)
                    summary = summarize(combined, model=obj.model, style="bullet", host=obj.host)
                    click.secho(summary, fg="white")
                    click.secho("─" * 60 + "\n", fg="magenta")

            except RuntimeError as exc:
                click.secho(f"⚠️  {exc}", fg="red", err=True)
                break
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    finally:
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    click.secho("\n─" * 60, fg="blue")
    full = "\n".join(all_text)
    click.secho(f"\n✅ หยุดบันทึก — {chunk_count} chunks, {len(full)} ตัวอักษร", fg="green")

    if output and full:
        Path(output).write_text(full, encoding="utf-8")
        click.secho(f"💾 บันทึกไว้ที่ {output}", fg="green")

    if do_summarize and full:
        click.secho("\n── สรุปสุดท้าย ──", fg="magenta", bold=True)
        summary = summarize(full, model=obj.model, style="action-items", host=obj.host)
        click.secho(summary, fg="white")

    if obj.json_output and full:
        import json as _json
        click.echo(_json.dumps({"chunks": chunk_count, "transcript": full}, ensure_ascii=False, indent=2))


# ===========================================================================
# Group: translate
# ===========================================================================

@cli.group()
@click.pass_obj
def translate_group(obj: AppContext) -> None:
    """Translate text between languages."""


cli.add_command(translate_group, name="translate")


@translate_group.command("text")
@click.argument("text", required=False)
@click.option("--from-lang", default="auto", show_default=True,
              help="Source language (use 'auto' to detect automatically).")
@click.option("--to-lang", default="th", show_default=True,
              help="Target language.")
@click.option("--output", "-o", default="", help="Save translation to this file.")
@click.pass_obj
def translate_text_cmd(
    obj: AppContext, text: Optional[str], from_lang: str, to_lang: str, output: str
) -> None:
    """Translate TEXT to target language.

    TEXT can be provided as an argument or piped through stdin.

    \b
    Examples:
      cli-anything-meeting translate text "Hello, world" --to-lang th
      echo "Good morning" | cli-anything-meeting translate text --from-lang en
    """
    if not text:
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            click.secho("Provide text as argument or pipe via stdin.", fg="red", err=True)
            sys.exit(1)

    click.secho(f"Translating ({from_lang} → {to_lang}) …", fg="cyan", err=True)
    try:
        result = translate(text, source_lang=from_lang, target_lang=to_lang,
                           model=obj.model, host=obj.host)
    except RuntimeError as exc:
        _error(obj, "Translation failed.", exc)
        sys.exit(1)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.secho(f"Translation saved to {output}", fg="green", err=True)

    _print_result(obj, {"result": result})


@translate_group.command("file")
@click.argument("input_file", type=click.Path(exists=True, readable=True))
@click.option("--from-lang", default="auto", show_default=True,
              help="Source language (use 'auto' to detect automatically).")
@click.option("--to-lang", default="th", show_default=True,
              help="Target language.")
@click.option("--output", "-o", default="",
              help="Output file path (default: <input>.<to_lang>.txt).")
@click.pass_obj
def translate_file_cmd(
    obj: AppContext, input_file: str, from_lang: str, to_lang: str, output: str
) -> None:
    """Translate INPUT_FILE to target language.

    \b
    Examples:
      cli-anything-meeting translate file transcript.txt --to-lang th
      cli-anything-meeting translate file notes_en.txt --from-lang en --to-lang th
    """
    text = Path(input_file).read_text(encoding="utf-8")

    click.secho(f"Translating {input_file} ({from_lang} → {to_lang}) …", fg="cyan", err=True)
    try:
        result = translate(text, source_lang=from_lang, target_lang=to_lang,
                           model=obj.model, host=obj.host)
    except RuntimeError as exc:
        _error(obj, "Translation failed.", exc)
        sys.exit(1)

    if not output:
        base = Path(input_file).stem
        output = str(Path(input_file).parent / f"{base}.{to_lang}.txt")

    Path(output).write_text(result, encoding="utf-8")
    click.secho(f"Saved to {output}", fg="green", err=True)

    _print_result(obj, {"result": result, "saved_to": output})


# ===========================================================================
# Group: summarize
# ===========================================================================

@cli.group()
@click.pass_obj
def summarize_group(obj: AppContext) -> None:
    """Summarize meeting content."""


cli.add_command(summarize_group, name="summarize")


@summarize_group.command("text")
@click.argument("text", required=False)
@click.option("--style", default="bullet", show_default=True,
              type=click.Choice(["bullet", "paragraph", "action-items"]),
              help="Summary output style.")
@click.option("--output", "-o", default="", help="Save summary to this file.")
@click.pass_obj
def summarize_text_cmd(
    obj: AppContext, text: Optional[str], style: str, output: str
) -> None:
    """Summarize TEXT (Thai output).

    TEXT can be provided as an argument or piped through stdin.

    \b
    Examples:
      cli-anything-meeting summarize text "The team discussed Q1 targets…"
      cat transcript.txt | cli-anything-meeting summarize text --style action-items
    """
    if not text:
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            click.secho("Provide text as argument or pipe via stdin.", fg="red", err=True)
            sys.exit(1)

    click.secho(f"Summarizing ({style}) …", fg="cyan", err=True)
    try:
        result = summarize(text, model=obj.model, style=style, host=obj.host)
    except RuntimeError as exc:
        _error(obj, "Summarization failed.", exc)
        sys.exit(1)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.secho(f"Summary saved to {output}", fg="green", err=True)

    _print_result(obj, {"summary": result})


@summarize_group.command("file")
@click.argument("input_file", type=click.Path(exists=True, readable=True))
@click.option("--style", default="bullet", show_default=True,
              type=click.Choice(["bullet", "paragraph", "action-items"]),
              help="Summary output style.")
@click.option("--output", "-o", default="", help="Save summary to this file.")
@click.pass_obj
def summarize_file_cmd(obj: AppContext, input_file: str, style: str, output: str) -> None:
    """Summarize INPUT_FILE (Thai output).

    \b
    Examples:
      cli-anything-meeting summarize file transcript.txt
      cli-anything-meeting summarize file notes.txt --style action-items
    """
    text = Path(input_file).read_text(encoding="utf-8")

    click.secho(f"Summarizing {input_file} ({style}) …", fg="cyan", err=True)
    try:
        result = summarize(text, model=obj.model, style=style, host=obj.host)
    except RuntimeError as exc:
        _error(obj, "Summarization failed.", exc)
        sys.exit(1)

    if not output:
        base = Path(input_file).stem
        output = str(Path(input_file).parent / f"{base}_summary.txt")

    Path(output).write_text(result, encoding="utf-8")
    click.secho(f"Summary saved to {output}", fg="green", err=True)

    _print_result(obj, {"summary": result, "saved_to": output})


@summarize_group.command("meeting")
@click.option("--file", "-f", "audio_file", default="",
              help="Use existing audio file instead of recording.")
@click.option("--duration", "-d", default=60, show_default=True,
              help="Recording duration in seconds (ignored when --file is given).")
@click.option("--lang", "-l", default="th", show_default=True,
              help="Spoken language in the audio.")
@click.option("--translate-to", default="th", show_default=True,
              help="Translate transcript to this language before summarizing.")
@click.option("--style", default="bullet", show_default=True,
              type=click.Choice(["bullet", "paragraph", "action-items"]),
              help="Summary output style.")
@click.option("--title", default="", help="Meeting title for the minutes file.")
@click.option("--output", "-o", default="",
              help="Output minutes file path (default: auto-generated).")
@click.option("--keep-audio", is_flag=True, default=False,
              help="Keep the recorded audio file (only relevant when recording).")
@click.pass_obj
def summarize_meeting(
    obj: AppContext,
    audio_file: str,
    duration: int,
    lang: str,
    translate_to: str,
    style: str,
    title: str,
    output: str,
    keep_audio: bool,
) -> None:
    """Full meeting pipeline: record → transcribe → translate → summarize → save.

    This is the primary command for end-to-end meeting processing.

    \b
    Steps:
      1. Record audio from microphone (or use --file for existing audio)
      2. Transcribe via Gemma 4 audio model
      3. Translate to Thai (or --translate-to language) if needed
      4. Summarize with action items
      5. Save as a markdown minutes file

    \b
    Examples:
      # Record a 5-minute meeting and produce Thai minutes
      cli-anything-meeting summarize meeting --duration 300

      # Use an existing recording
      cli-anything-meeting summarize meeting --file standup.wav --title "Daily Standup"

      # English meeting, translate to Thai, action-items style
      cli-anything-meeting summarize meeting --duration 60 --lang en --style action-items
    """
    tmp_audio: Optional[str] = None
    pipeline_steps: list[str] = []

    try:
        # ------------------------------------------------------------------
        # Step 1: Obtain audio
        # ------------------------------------------------------------------
        if audio_file:
            if not Path(audio_file).exists():
                _error(obj, f"Audio file not found: {audio_file}")
                sys.exit(1)
            recording_path = audio_file
            click.secho(f"Using audio file: {recording_path}", fg="cyan", err=True)
        else:
            recordings_dir = MINUTES_DIR / "recordings"
            recordings_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            recording_path = str(recordings_dir / f"meeting_{ts}.wav")
            tmp_audio = recording_path if not keep_audio else None

            click.secho(
                f"[1/4] Recording {duration}s …  (Ctrl+C to cancel)",
                fg="yellow", err=True,
            )
            record_audio(duration, recording_path, host=obj.host)
            pipeline_steps.append(f"Recorded: {recording_path}")
            click.secho("      Recording complete.", fg="green", err=True)

        # ------------------------------------------------------------------
        # Step 2: Transcribe
        # ------------------------------------------------------------------
        click.secho("[2/4] Transcribing audio …", fg="yellow", err=True)
        transcript = transcribe(recording_path, model=obj.model, language=lang, host=obj.host)
        pipeline_steps.append("Transcription: done")
        click.secho("      Transcription complete.", fg="green", err=True)

        # ------------------------------------------------------------------
        # Step 3: Translate (if source != target)
        # ------------------------------------------------------------------
        lang_normalised = lang.lower().strip()
        translate_normalised = translate_to.lower().strip()
        needs_translation = lang_normalised != translate_normalised

        if needs_translation:
            click.secho(
                f"[3/4] Translating ({lang} → {translate_to}) …",
                fg="yellow", err=True,
            )
            working_text = translate(
                transcript,
                source_lang=lang,
                target_lang=translate_to,
                model=obj.model,
                host=obj.host,
            )
            pipeline_steps.append(f"Translation ({lang}→{translate_to}): done")
            click.secho("      Translation complete.", fg="green", err=True)
        else:
            working_text = transcript
            pipeline_steps.append("Translation: skipped (same language)")

        # ------------------------------------------------------------------
        # Step 4: Summarize
        # ------------------------------------------------------------------
        click.secho(f"[4/4] Summarizing ({style}) …", fg="yellow", err=True)
        summary = summarize(working_text, model=obj.model, style=style, host=obj.host)
        pipeline_steps.append(f"Summary ({style}): done")
        click.secho("      Summary complete.", fg="green", err=True)

        # ------------------------------------------------------------------
        # Step 5: Assemble minutes content
        # ------------------------------------------------------------------
        sections = []

        sections.append("## บทสรุปการประชุม\n")
        sections.append(summary)
        sections.append("")

        sections.append("## คำบันทึกถ้อยคำ (Transcript)\n")
        sections.append(transcript)
        sections.append("")

        if needs_translation:
            sections.append(f"## คำแปล ({translate_to})\n")
            sections.append(working_text)
            sections.append("")

        minutes_content = "\n".join(sections)

        # ------------------------------------------------------------------
        # Step 6: Save
        # ------------------------------------------------------------------
        if not output:
            MINUTES_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = title.replace(" ", "_").lower()[:30] if title else "meeting"
            output = str(MINUTES_DIR / f"minutes_{slug}_{ts}.md")

        meeting_title = title or f"การประชุม {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        saved_path = save_minutes(
            minutes_content,
            output,
            title=meeting_title,
            metadata={"model": obj.model, "lang": lang, "style": style},
        )
        pipeline_steps.append(f"Minutes saved: {saved_path}")

        # ------------------------------------------------------------------
        # Output
        # ------------------------------------------------------------------
        click.secho(f"\nMinutes saved to: {saved_path}", fg="green")
        click.secho("─" * 60, fg="bright_black", err=True)
        click.secho("Summary:", fg="bright_white")
        click.echo(summary)

        if obj.output_json:
            click.echo(json.dumps({
                "ok": True,
                "minutes_file": saved_path,
                "transcript": transcript,
                "translation": working_text if needs_translation else None,
                "summary": summary,
                "pipeline": pipeline_steps,
            }, ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        click.secho("\nPipeline cancelled by user.", fg="red", err=True)
        sys.exit(130)
    except (RuntimeError, FileNotFoundError) as exc:
        _error(obj, "Meeting pipeline failed.", exc)
        sys.exit(1)
    finally:
        # Clean up temp audio unless --keep-audio was passed
        if tmp_audio and not keep_audio:
            try:
                os.unlink(tmp_audio)
            except OSError:
                pass


# ===========================================================================
# Group: minutes
# ===========================================================================

@cli.group()
@click.pass_obj
def minutes_group(obj: AppContext) -> None:
    """Manage meeting minutes files."""


cli.add_command(minutes_group, name="minutes")


@minutes_group.command("save")
@click.argument("text", required=False)
@click.option("--title", "-t", default="", help="Meeting title.")
@click.option("--output", "-o", default="",
              help="Output file path (default: auto-generated).")
@click.pass_obj
def minutes_save(obj: AppContext, text: Optional[str], title: str, output: str) -> None:
    """Save TEXT as a markdown meeting minutes file.

    TEXT can be provided as an argument or piped through stdin.

    \b
    Examples:
      cat summary.txt | cli-anything-meeting minutes save --title "Sprint Review"
      cli-anything-meeting minutes save "Action: Fix bug #42" --title "Daily Standup"
    """
    if not text:
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            click.secho("Provide text as argument or pipe via stdin.", fg="red", err=True)
            sys.exit(1)

    if not output:
        MINUTES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = title.replace(" ", "_").lower()[:30] if title else "minutes"
        output = str(MINUTES_DIR / f"{slug}_{ts}.md")

    saved = save_minutes(text, output, title=title)
    click.secho(f"Minutes saved to: {saved}", fg="green")
    _print_result(obj, {"saved_to": saved})


@minutes_group.command("list")
@click.option("--dir", "minutes_dir", default="",
              help="Directory to list (default: ~/meeting_minutes/).")
@click.option("--limit", "-n", default=20, show_default=True,
              help="Maximum number of entries to show.")
@click.pass_obj
def minutes_list(obj: AppContext, minutes_dir: str, limit: int) -> None:
    """List saved meeting minutes files."""
    search_dir = Path(minutes_dir).expanduser() if minutes_dir else MINUTES_DIR

    if not search_dir.exists():
        click.secho(f"No minutes directory found at {search_dir}", fg="yellow", err=True)
        if obj.output_json:
            click.echo(json.dumps({"files": []}, indent=2))
        return

    files = sorted(
        search_dir.glob("*.md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:limit]

    if obj.output_json:
        click.echo(json.dumps({"files": [str(f) for f in files]}, indent=2))
        return

    if not files:
        click.secho("No minutes files found.", fg="yellow")
        return

    click.secho(f"Minutes in {search_dir}:", fg="bright_white")
    for i, f in enumerate(files, 1):
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size_kb = f.stat().st_size // 1024
        click.echo(f"  {i:>3}. {mtime}  {size_kb:>4}KB  {f.name}")


@minutes_group.command("view")
@click.argument("minutes_file", required=False)
@click.option("--index", "-i", default=0,
              help="View minutes by index from `minutes list` (1-based).")
@click.pass_obj
def minutes_view(obj: AppContext, minutes_file: Optional[str], index: int) -> None:
    """View a meeting minutes file.

    Provide either a file path or use --index to pick from the list.

    \b
    Examples:
      cli-anything-meeting minutes view minutes_20240105_143000.md
      cli-anything-meeting minutes view --index 1   # view most recent
    """
    if not minutes_file and index:
        files = sorted(
            MINUTES_DIR.glob("*.md") if MINUTES_DIR.exists() else [],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if index < 1 or index > len(files):
            _error(obj, f"Index {index} out of range (1–{len(files)}).")
            sys.exit(1)
        minutes_file = str(files[index - 1])

    if not minutes_file:
        _error(obj, "Provide a file path or use --index.")
        sys.exit(1)

    path = Path(minutes_file).expanduser()
    if not path.exists():
        # Try relative to MINUTES_DIR
        path = MINUTES_DIR / minutes_file
        if not path.exists():
            _error(obj, f"File not found: {minutes_file}")
            sys.exit(1)

    content = path.read_text(encoding="utf-8")
    if obj.output_json:
        click.echo(json.dumps({"file": str(path), "content": content}, ensure_ascii=False, indent=2))
    else:
        click.secho(f"=== {path.name} ===", fg="bright_white")
        click.echo(content)


# ===========================================================================
# REPL mode
# ===========================================================================

@cli.command("repl")
@click.pass_obj
def repl_mode(obj: AppContext) -> None:
    """Interactive REPL mode for the Meeting Assistant.

    Type commands without the 'cli-anything-meeting' prefix.
    Type 'help' to see available commands, 'exit' or 'quit' to leave.

    \b
    Examples:
      > transcribe audio meeting.wav
      > summarize text "Today we agreed to..."
      > minutes list
    """
    session: PromptSession = PromptSession(history=InMemoryHistory())

    click.secho("Meeting Assistant REPL", fg="bright_cyan", bold=True)
    click.secho(f"Model: {obj.model}  |  Host: {obj.host}", fg="cyan")
    click.secho("Type 'help' for commands, 'exit' to quit.\n", fg="bright_black")

    while True:
        try:
            line = session.prompt("meeting> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.secho("\nBye!", fg="cyan")
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit", "q", ":q"):
            click.secho("Bye!", fg="cyan")
            break

        if line.lower() in ("help", "?", "h"):
            click.secho(
                "\nAvailable commands (omit 'cli-anything-meeting' prefix):\n"
                "  record start [--duration N] [--output FILE]\n"
                "  record list\n"
                "  transcribe audio FILE [--lang LANG]\n"
                "  transcribe live [--duration N] [--lang LANG]\n"
                "  translate text TEXT [--from-lang LANG] [--to-lang LANG]\n"
                "  translate file FILE [--from-lang LANG] [--to-lang LANG]\n"
                "  summarize text TEXT [--style bullet|paragraph|action-items]\n"
                "  summarize file FILE [--style ...]\n"
                "  summarize meeting [--duration N] [--file F] [--title T]\n"
                "  minutes save [TEXT] [--title T] [--output FILE]\n"
                "  minutes list\n"
                "  minutes view [FILE | --index N]\n"
                "  exit / quit\n",
                fg="bright_white",
            )
            continue

        # Invoke the CLI recursively by reconstructing argv
        import shlex
        try:
            args = shlex.split(line)
        except ValueError as exc:
            click.secho(f"Parse error: {exc}", fg="red")
            continue

        try:
            # standalone_mode=False prevents SystemExit on errors
            cli.main(
                args=args,
                obj=obj,
                standalone_mode=False,
                prog_name="cli-anything-meeting",
            )
        except click.UsageError as exc:
            click.secho(f"Usage error: {exc}", fg="red")
        except click.Abort:
            click.secho("Aborted.", fg="yellow")
        except SystemExit:
            pass
        except Exception as exc:  # noqa: BLE001
            click.secho(f"Error: {exc}", fg="red")


# ===========================================================================
# Entry point guard
# ===========================================================================

if __name__ == "__main__":
    cli()
