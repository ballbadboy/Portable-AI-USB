#!/usr/bin/env python3
"""Joplin CLI — A command-line interface for the Joplin note-taking app.

This CLI provides full access to the Joplin REST API (Web Clipper service)
for managing notes, notebooks, tags, and performing searches — all without
opening the Joplin GUI.

Usage:
    # One-shot commands
    cli-anything-joplin note list
    cli-anything-joplin note get <id>
    cli-anything-joplin --json note search "meeting"

    # Interactive REPL
    cli-anything-joplin
"""

import os
import sys
import json
import shlex
import click
from typing import Optional

from cli_anything.joplin.utils.joplin_backend import DEFAULT_BASE_URL, JoplinBackend

# ── Global session state ─────────────────────────────────────────────────────
_json_output: bool = False
_repl_mode: bool = False
_host: str = DEFAULT_BASE_URL
_token: str = ""
_backend: JoplinBackend | None = None

VERSION = "1.0.0"


# ── Backend accessor ─────────────────────────────────────────────────────────

def _get_backend() -> JoplinBackend:
    """Return the shared JoplinBackend, lazily initialised."""
    global _backend
    if _backend is None or _backend.base_url != _host or _backend.token != _token:
        _backend = JoplinBackend(base_url=_host, token=_token or None)
    return _backend


# ── Output helpers ───────────────────────────────────────────────────────────

def output(data, message: str = ""):
    """Print data either as JSON or human-readable text."""
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.echo(message)
        if isinstance(data, dict):
            _print_dict(data)
        elif isinstance(data, list):
            _print_list(data)
        else:
            click.echo(str(data))


def _print_dict(d: dict, indent: int = 0):
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            click.echo(f"{prefix}{k}:")
            _print_dict(v, indent + 1)
        elif isinstance(v, list):
            click.echo(f"{prefix}{k}:")
            _print_list(v, indent + 1)
        else:
            click.echo(f"{prefix}{k}: {v}")


def _print_list(items: list, indent: int = 0):
    prefix = "  " * indent
    for i, item in enumerate(items):
        if isinstance(item, dict):
            click.echo(f"{prefix}[{i}]")
            _print_dict(item, indent + 1)
        else:
            click.echo(f"{prefix}- {item}")


def _format_ts(ms: int | None) -> str:
    """Format a Joplin millisecond timestamp as a readable string."""
    if not ms:
        return ""
    import datetime
    dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M")


# ── Error handling decorator ─────────────────────────────────────────────────

def handle_error(func):
    """Decorator: catch RuntimeError/ValueError and print cleanly."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RuntimeError as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": "runtime_error"}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
        except (ValueError, KeyError, IndexError) as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": type(e).__name__}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ── Main CLI group ───────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True,
              help="Output results as JSON (for agent/script consumption)")
@click.option("--host", type=str, default=None,
              help=f"Joplin API base URL (default: {DEFAULT_BASE_URL})")
@click.option("--token", type=str, default=None, envvar="JOPLIN_TOKEN",
              help="Joplin API token (or set JOPLIN_TOKEN env var)")
@click.pass_context
def cli(ctx, use_json, host, token):
    """Joplin CLI — Note management via the Joplin Web Clipper REST API.

    Run without a subcommand to enter interactive REPL mode.

    \b
    Quick start:
      cli-anything-joplin --token <TOKEN> note list
      cli-anything-joplin --token <TOKEN> note search "meeting"
      cli-anything-joplin --token <TOKEN> --json note list
    """
    global _json_output, _host, _token
    _json_output = use_json
    if host:
        _host = host
    if token:
        _token = token
    elif not _token:
        # Try environment variable (already handled by envvar= but fallback)
        _token = os.environ.get("JOPLIN_TOKEN", "")

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ── Note group ───────────────────────────────────────────────────────────────

@cli.group()
def note():
    """Note management commands."""
    pass


@note.command("list")
@click.option("--limit", "-l", default=50, show_default=True,
              help="Maximum number of notes to return")
@click.option("--page", "-p", default=1, show_default=True,
              help="Page number (1-based)")
@handle_error
def note_list(limit, page):
    """List notes, most-recently-updated first."""
    backend = _get_backend()
    result = backend.list_notes(limit=limit, page=page)
    items = result.get("items", [])
    has_more = result.get("has_more", False)

    if _json_output:
        output(result)
        return

    if not items:
        click.echo("No notes found.")
        return

    click.echo(f"{'TITLE':<50} {'UPDATED':<17} {'ID'}")
    click.echo("─" * 90)
    for n in items:
        title = (n.get("title") or "(untitled)")[:48]
        updated = _format_ts(n.get("updated_time"))
        nid = n.get("id", "")[:8] + "..."
        click.echo(f"{title:<50} {updated:<17} {nid}")

    if has_more:
        click.echo(f"\n  (more results — use --page {page + 1} to continue)")


@note.command("get")
@click.argument("note_id")
@handle_error
def note_get(note_id):
    """Get a note's full content by ID."""
    backend = _get_backend()
    result = backend.get_note(note_id)

    if _json_output:
        output(result)
        return

    title = result.get("title", "(untitled)")
    body = result.get("body", "")
    nid = result.get("id", "")
    updated = _format_ts(result.get("updated_time"))
    created = _format_ts(result.get("created_time"))
    parent = result.get("parent_id", "")

    click.echo(f"Title:    {title}")
    click.echo(f"ID:       {nid}")
    click.echo(f"Notebook: {parent}")
    click.echo(f"Created:  {created}")
    click.echo(f"Updated:  {updated}")
    click.echo("─" * 60)
    click.echo(body)


@note.command("create")
@click.option("--title", "-t", required=True, help="Note title")
@click.option("--body", "-b", default="", help="Note body (Markdown)")
@click.option("--body-file", type=click.Path(exists=True), default=None,
              help="Read note body from a file")
@click.option("--notebook", "-n", "notebook_id", default=None,
              help="Target notebook ID (defaults to Joplin default)")
@handle_error
def note_create(title, body, body_file, notebook_id):
    """Create a new note."""
    backend = _get_backend()

    if body_file:
        with open(body_file, "r", encoding="utf-8") as fh:
            body = fh.read()

    result = backend.create_note(title=title, body=body, notebook_id=notebook_id)

    if _json_output:
        output(result)
        return

    nid = result.get("id", "")
    click.echo(f"Created note '{title}' with ID: {nid}")


@note.command("edit")
@click.argument("note_id")
@click.option("--title", "-t", default=None, help="New title")
@click.option("--body", "-b", default=None, help="New body (Markdown)")
@click.option("--body-file", type=click.Path(exists=True), default=None,
              help="Read new body from a file")
@handle_error
def note_edit(note_id, title, body, body_file):
    """Update an existing note's title and/or body."""
    backend = _get_backend()

    if body_file:
        with open(body_file, "r", encoding="utf-8") as fh:
            body = fh.read()

    if title is None and body is None:
        raise ValueError("Provide at least --title or --body (or --body-file).")

    result = backend.update_note(note_id=note_id, title=title, body=body)

    if _json_output:
        output(result)
        return

    click.echo(f"Updated note {note_id}")


@note.command("delete")
@click.argument("note_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_error
def note_delete(note_id, yes):
    """Permanently delete a note by ID."""
    backend = _get_backend()

    if not yes and not _repl_mode:
        click.confirm(f"Delete note {note_id}? This cannot be undone.", abort=True)

    result = backend.delete_note(note_id)

    if _json_output:
        output(result)
        return

    click.echo(f"Deleted note {note_id}")


@note.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=20, show_default=True,
              help="Maximum results to return")
@handle_error
def note_search(query, limit):
    """Full-text search across all notes."""
    backend = _get_backend()
    result = backend.search(query=query, limit=limit)
    items = result.get("items", [])

    if _json_output:
        output(result)
        return

    if not items:
        click.echo(f"No notes found for query: {query!r}")
        return

    click.echo(f"Found {len(items)} result(s) for {query!r}:\n")
    click.echo(f"{'TITLE':<50} {'UPDATED':<17} {'ID'}")
    click.echo("─" * 90)
    for n in items:
        title = (n.get("title") or "(untitled)")[:48]
        updated = _format_ts(n.get("updated_time"))
        nid = n.get("id", "")[:8] + "..."
        click.echo(f"{title:<50} {updated:<17} {nid}")


# ── Notebook group ───────────────────────────────────────────────────────────

@cli.group()
def notebook():
    """Notebook (folder) management commands."""
    pass


@notebook.command("list")
@click.option("--limit", "-l", default=100, show_default=True,
              help="Maximum number of notebooks to return")
@handle_error
def notebook_list(limit):
    """List all notebooks."""
    backend = _get_backend()
    result = backend.list_notebooks(limit=limit)
    items = result.get("items", [])

    if _json_output:
        output(result)
        return

    if not items:
        click.echo("No notebooks found.")
        return

    click.echo(f"{'TITLE':<40} {'PARENT':<10} {'ID'}")
    click.echo("─" * 72)
    for nb in items:
        title = (nb.get("title") or "(untitled)")[:38]
        parent = (nb.get("parent_id") or "root")[:8]
        nid = nb.get("id", "")[:8] + "..."
        click.echo(f"{title:<40} {parent:<10} {nid}")


@notebook.command("create")
@click.option("--title", "-t", required=True, help="Notebook title")
@click.option("--parent", "-p", "parent_id", default=None,
              help="Parent notebook ID (omit for root-level)")
@handle_error
def notebook_create(title, parent_id):
    """Create a new notebook."""
    backend = _get_backend()
    result = backend.create_notebook(title=title, parent_id=parent_id)

    if _json_output:
        output(result)
        return

    nid = result.get("id", "")
    click.echo(f"Created notebook '{title}' with ID: {nid}")


@notebook.command("delete")
@click.argument("notebook_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_error
def notebook_delete(notebook_id, yes):
    """Delete a notebook and all notes inside it."""
    backend = _get_backend()

    if not yes and not _repl_mode:
        click.confirm(
            f"Delete notebook {notebook_id} and ALL its notes? This cannot be undone.",
            abort=True
        )

    result = backend.delete_notebook(notebook_id)

    if _json_output:
        output(result)
        return

    click.echo(f"Deleted notebook {notebook_id}")


# ── Tag group ────────────────────────────────────────────────────────────────

@cli.group()
def tag():
    """Tag management commands."""
    pass


@tag.command("list")
@click.option("--limit", "-l", default=100, show_default=True,
              help="Maximum number of tags to return")
@handle_error
def tag_list(limit):
    """List all tags."""
    backend = _get_backend()
    result = backend.list_tags(limit=limit)
    items = result.get("items", [])

    if _json_output:
        output(result)
        return

    if not items:
        click.echo("No tags found.")
        return

    click.echo(f"{'TITLE':<40} {'ID'}")
    click.echo("─" * 55)
    for t in items:
        title = (t.get("title") or "(untitled)")[:38]
        tid = t.get("id", "")[:8] + "..."
        click.echo(f"{title:<40} {tid}")


@tag.command("add")
@click.argument("note_id")
@click.argument("tag_id")
@handle_error
def tag_add(note_id, tag_id):
    """Apply an existing tag to a note.

    \b
    Arguments:
      NOTE_ID   ID of the note to tag
      TAG_ID    ID of the tag to apply
    """
    backend = _get_backend()
    result = backend.add_tag(note_id=note_id, tag_id=tag_id)

    if _json_output:
        output(result)
        return

    click.echo(f"Tag {tag_id} applied to note {note_id}")


# ── Session group ────────────────────────────────────────────────────────────

@cli.group()
def session():
    """Session and connection state commands."""
    pass


@session.command("status")
@handle_error
def session_status():
    """Show current session configuration and connectivity."""
    backend = _get_backend()
    available = backend.is_available()

    data = {
        "host": _host,
        "token_set": bool(_token),
        "token_preview": (_token[:4] + "..." + _token[-4:]) if len(_token) > 8 else ("(set)" if _token else "(not set)"),
        "api_reachable": available,
        "json_output": _json_output,
    }

    if _json_output:
        output(data)
        return

    status_icon = "online" if available else "offline"
    click.echo(f"Host:          {_host}")
    click.echo(f"API status:    {status_icon}")
    click.echo(f"Token set:     {'yes' if _token else 'no'}")
    if _token:
        preview = (_token[:4] + "..." + _token[-4:]) if len(_token) > 8 else "(set)"
        click.echo(f"Token:         {preview}")
    click.echo(f"JSON output:   {_json_output}")


# ── REPL ─────────────────────────────────────────────────────────────────────

@cli.command()
@handle_error
def repl():
    """Start an interactive REPL session."""
    from cli_anything.joplin.utils.repl_skin import ReplSkin

    global _repl_mode
    _repl_mode = True

    skin = ReplSkin("joplin", version=VERSION)
    skin.print_banner()

    if not _token:
        skin.warning(
            "No API token set. Pass --token <TOKEN> or set JOPLIN_TOKEN env var."
        )
        skin.hint("  Get your token: Joplin → Tools → Options → Web Clipper")
    else:
        skin.info(f"Connected to {_host}")

    pt_session = skin.create_prompt_session()

    _repl_commands = {
        "note":     "list | get | create | edit | delete | search",
        "notebook": "list | create | delete",
        "tag":      "list | add",
        "session":  "status",
        "help":     "Show this help",
        "quit":     "Exit REPL",
    }

    while True:
        try:
            line = skin.get_input(pt_session, project_name="", modified=False)
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                skin.print_goodbye()
                break
            if line.lower() == "help":
                skin.help(_repl_commands)
                continue

            try:
                args = shlex.split(line)
            except ValueError:
                args = line.split()

            try:
                cli.main(args, standalone_mode=False)
            except SystemExit:
                pass
            except click.exceptions.UsageError as e:
                skin.warning(f"Usage error: {e}")
            except Exception as e:
                skin.error(f"{e}")

        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

    _repl_mode = False


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
