"""
plantuml_cli.py
~~~~~~~~~~~~~~~
Full Click CLI for cli-anything-plantuml.

Usage
-----
  cli-anything-plantuml [--json] <group> <command> [options]
  cli-anything-plantuml repl

Groups
------
  diagram   render / validate / preview
  template  list / show / use
  server    status

Global flags
------------
  --json    Emit all output as JSON (machine-readable)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory

from cli_anything.plantuml.utils.plantuml_backend import (
    TEMPLATES,
    PlantUMLNotFoundError,
    PlantUMLRenderError,
    find_plantuml,
    render,
    validate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_MODE_KEY = "json_mode"


def _ctx_json(ctx: click.Context) -> bool:
    """Return True if --json was passed at the top-level group."""
    return bool(ctx.find_root().ensure_object(dict).get(_JSON_MODE_KEY))


def _out(ctx: click.Context, data: dict) -> None:
    """Emit either JSON or human-readable output depending on --json flag."""
    if _ctx_json(ctx):
        click.echo(json.dumps(data, indent=2))
    else:
        # Human-readable: print each key=value pair sensibly
        for key, value in data.items():
            if key == "error":
                click.secho(f"Error: {value}", fg="red", err=True)
            elif key == "message":
                click.echo(value)
            elif key == "output":
                # Large text/svg output — print as-is
                click.echo(value)
            elif key == "templates":
                for name in value:
                    click.echo(f"  {name}")
            elif key == "source":
                click.echo(value)
            elif isinstance(value, bool):
                label = click.style("yes" if value else "no", fg="green" if value else "red")
                click.echo(f"{key}: {label}")
            else:
                click.echo(f"{key}: {value}")


def _err(ctx: click.Context, message: str, exit_code: int = 1) -> None:
    _out(ctx, {"error": message, "success": False})
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool) -> None:
    """CLI-Anything harness for PlantUML diagram generation.

    \b
    Examples:
      cli-anything-plantuml diagram render --source "@startuml\\nA->B\\n@enduml" --format svg
      cli-anything-plantuml diagram validate --file my.puml
      cli-anything-plantuml template list
      cli-anything-plantuml template use sequence --output seq.puml
      cli-anything-plantuml server status
      cli-anything-plantuml repl
    """
    ctx.ensure_object(dict)
    ctx.obj[_JSON_MODE_KEY] = json_mode


# ---------------------------------------------------------------------------
# Group: diagram
# ---------------------------------------------------------------------------


@cli.group()
def diagram() -> None:
    """Commands for rendering and validating PlantUML diagrams."""


def _resolve_source(source: Optional[str], file: Optional[str], ctx: click.Context) -> str:
    """Return source text, reading from file if necessary."""
    if source and file:
        _err(ctx, "Specify either --source or --file, not both.")
    if file:
        path = Path(file)
        if not path.exists():
            _err(ctx, f"File not found: {file}")
        return path.read_text(encoding="utf-8")
    if source:
        return source
    # Try reading from stdin if it's piped
    if not sys.stdin.isatty():
        return sys.stdin.read()
    _err(ctx, "Provide --source, --file, or pipe input via stdin.")
    return ""  # unreachable


@diagram.command("render")
@click.option("--source", "-s", default=None, help="PlantUML source text.")
@click.option("--file", "-f", "file", default=None, help="Path to .puml source file.")
@click.option(
    "--format",
    "-F",
    "fmt",
    default="svg",
    type=click.Choice(["svg", "png", "pdf", "txt"], case_sensitive=False),
    show_default=True,
    help="Output format.",
)
@click.option("--output", "-o", default=None, help="Output file path (default: stdout for svg/txt).")
@click.pass_context
def diagram_render(
    ctx: click.Context,
    source: Optional[str],
    file: Optional[str],
    fmt: str,
    output: Optional[str],
) -> None:
    """Render a PlantUML diagram to SVG, PNG, PDF, or TXT.

    \b
    Examples:
      # Render inline source to SVG on stdout
      cli-anything-plantuml diagram render --source "@startuml\\nA->B\\n@enduml"

      # Render a file to PNG, save to disk
      cli-anything-plantuml diagram render --file diagram.puml --format png --output out.png
    """
    src = _resolve_source(source, file, ctx)
    try:
        data = render(src, format=fmt)
    except PlantUMLNotFoundError as exc:
        _err(ctx, str(exc))
    except PlantUMLRenderError as exc:
        _err(ctx, str(exc))

    if output:
        out_path = Path(output)
        out_path.write_bytes(data)
        _out(ctx, {"success": True, "message": f"Rendered to {out_path}", "format": fmt, "bytes": len(data)})
    else:
        # Write bytes to stdout for binary formats; decode for text
        if fmt in ("svg", "txt"):
            text = data.decode("utf-8", errors="replace")
            if _ctx_json(ctx):
                _out(ctx, {"success": True, "format": fmt, "output": text})
            else:
                click.echo(text, nl=False)
        else:
            # Binary formats: write raw bytes to stdout buffer
            if _ctx_json(ctx):
                import base64
                _out(ctx, {"success": True, "format": fmt, "output_base64": base64.b64encode(data).decode()})
            else:
                sys.stdout.buffer.write(data)


@diagram.command("validate")
@click.option("--source", "-s", default=None, help="PlantUML source text.")
@click.option("--file", "-f", "file", default=None, help="Path to .puml source file.")
@click.pass_context
def diagram_validate(
    ctx: click.Context,
    source: Optional[str],
    file: Optional[str],
) -> None:
    """Check if PlantUML source is syntactically valid.

    \b
    Examples:
      cli-anything-plantuml diagram validate --file my.puml
      echo "@startuml\\nA->B\\n@enduml" | cli-anything-plantuml diagram validate
    """
    src = _resolve_source(source, file, ctx)
    try:
        result = validate(src)
    except PlantUMLNotFoundError as exc:
        _err(ctx, str(exc))
        return

    if result:
        _out(ctx, {"valid": True, "message": "Syntax is valid."})
    else:
        _out(ctx, {"valid": False, "message": "Syntax is invalid."})
        if not _ctx_json(ctx):
            sys.exit(1)


@diagram.command("preview")
@click.option("--source", "-s", default=None, help="PlantUML source text.")
@click.option("--file", "-f", "file", default=None, help="Path to .puml source file.")
@click.pass_context
def diagram_preview(
    ctx: click.Context,
    source: Optional[str],
    file: Optional[str],
) -> None:
    """Render a diagram and open it in the default viewer.

    Renders to SVG and opens with the system default application.

    \b
    Examples:
      cli-anything-plantuml diagram preview --file my.puml
    """
    import tempfile
    import subprocess
    import platform

    src = _resolve_source(source, file, ctx)
    try:
        data = render(src, format="svg")
    except PlantUMLNotFoundError as exc:
        _err(ctx, str(exc))
    except PlantUMLRenderError as exc:
        _err(ctx, str(exc))

    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    system = platform.system()
    if system == "Darwin":
        open_cmd = ["open", tmp_path]
    elif system == "Windows":
        open_cmd = ["start", tmp_path]
    else:
        open_cmd = ["xdg-open", tmp_path]

    try:
        subprocess.Popen(open_cmd)
        _out(ctx, {"success": True, "message": f"Opened preview: {tmp_path}"})
    except FileNotFoundError:
        _out(ctx, {
            "success": False,
            "message": f"Could not open viewer. SVG saved to: {tmp_path}",
        })


# ---------------------------------------------------------------------------
# Group: template
# ---------------------------------------------------------------------------


@cli.group()
def template() -> None:
    """Manage and use built-in PlantUML diagram templates."""


@template.command("list")
@click.pass_context
def template_list(ctx: click.Context) -> None:
    """List all available diagram templates.

    \b
    Available templates: sequence, class, activity, usecase,
    component, state, er, mindmap
    """
    names = sorted(TEMPLATES.keys())
    if _ctx_json(ctx):
        _out(ctx, {"templates": names, "count": len(names)})
    else:
        click.echo(click.style("Available templates:", bold=True))
        for name in names:
            click.echo(f"  {click.style(name, fg='cyan')}")
        click.echo(f"\n{len(names)} templates available.")


@template.command("show")
@click.argument("name")
@click.pass_context
def template_show(ctx: click.Context, name: str) -> None:
    """Display the source for a named template.

    \b
    Example:
      cli-anything-plantuml template show sequence
    """
    key = name.lower()
    if key not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES.keys()))
        _err(ctx, f"Template {name!r} not found. Available: {available}")

    src = TEMPLATES[key]
    if _ctx_json(ctx):
        _out(ctx, {"name": key, "source": src})
    else:
        click.echo(click.style(f"-- {key} template --", bold=True, fg="cyan"))
        click.echo(src)


@template.command("use")
@click.argument("name")
@click.option("--output", "-o", default=None, help="Output file path (default: stdout).")
@click.pass_context
def template_use(ctx: click.Context, name: str, output: Optional[str]) -> None:
    """Output a template to a file or stdout, ready to edit and render.

    \b
    Examples:
      # Print to stdout
      cli-anything-plantuml template use sequence

      # Save to file
      cli-anything-plantuml template use class --output class_diagram.puml
    """
    key = name.lower()
    if key not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES.keys()))
        _err(ctx, f"Template {name!r} not found. Available: {available}")

    src = TEMPLATES[key]

    if output:
        out_path = Path(output)
        out_path.write_text(src, encoding="utf-8")
        _out(ctx, {"success": True, "message": f"Template written to {out_path}", "name": key})
    else:
        if _ctx_json(ctx):
            _out(ctx, {"name": key, "source": src})
        else:
            click.echo(src, nl=False)


# ---------------------------------------------------------------------------
# Group: server
# ---------------------------------------------------------------------------


@cli.group()
def server() -> None:
    """Check PlantUML server/installation status."""


@server.command("status")
@click.pass_context
def server_status(ctx: click.Context) -> None:
    """Check whether PlantUML is available and show invocation details.

    \b
    Example:
      cli-anything-plantuml server status
    """
    cmd = find_plantuml()
    if cmd is None:
        _out(ctx, {
            "available": False,
            "message": (
                "PlantUML not found. Install with:\n"
                "  brew install plantuml          (macOS)\n"
                "  sudo apt install plantuml      (Debian/Ubuntu)\n"
                "  choco install plantuml         (Windows)\n"
                "Or set PLANTUML_JAR=/path/to/plantuml.jar"
            ),
        })
        sys.exit(1)

    invocation = " ".join(cmd)

    # Quick smoke-test: render a tiny diagram
    smoke = "@startuml\nA -> B\n@enduml\n"
    try:
        render(smoke, format="svg")
        render_ok = True
        render_msg = "Render smoke-test passed."
    except PlantUMLRenderError as exc:
        render_ok = False
        render_msg = str(exc)

    _out(ctx, {
        "available": True,
        "invocation": invocation,
        "render_ok": render_ok,
        "message": render_msg,
    })


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

_REPL_COMMANDS = [
    "diagram render",
    "diagram validate",
    "diagram preview",
    "template list",
    "template show",
    "template use",
    "server status",
    "help",
    "exit",
    "quit",
]


@cli.command("repl")
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Start an interactive REPL for PlantUML commands.

    Type commands without the 'cli-anything-plantuml' prefix.
    Type 'help' for available commands, 'exit' or 'quit' to leave.

    \b
    Example session:
      > server status
      > template list
      > template use sequence
      > diagram render --source "@startuml\\nA->B\\n@enduml"
    """
    completer = WordCompleter(
        _REPL_COMMANDS,
        sentence=True,
        ignore_case=True,
    )
    session: PromptSession = PromptSession(
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
    )

    json_mode = _ctx_json(ctx)

    click.secho("cli-anything-plantuml REPL", bold=True, fg="cyan")
    click.echo("Type 'help' for available commands, 'exit' to quit.\n")

    while True:
        try:
            raw = session.prompt("plantuml> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nExiting REPL.")
            break

        if not raw:
            continue

        if raw.lower() in ("exit", "quit"):
            click.echo("Goodbye.")
            break

        if raw.lower() == "help":
            click.secho("Available commands:", bold=True)
            for cmd_name in _REPL_COMMANDS:
                click.echo(f"  {cmd_name}")
            continue

        # Prepend the program name and re-invoke Click
        args = raw.split()
        # Build a standalone invocation so Click parses it fresh
        try:
            # Re-invoke through the cli group; catch SystemExit
            standalone_args = []
            if json_mode:
                standalone_args.append("--json")
            standalone_args.extend(args)
            cli.main(args=standalone_args, standalone_mode=False, obj={_JSON_MODE_KEY: json_mode})
        except click.UsageError as exc:
            click.secho(f"Usage error: {exc}", fg="red", err=True)
        except click.ClickException as exc:
            exc.show()
        except SystemExit:
            pass
        except Exception as exc:  # noqa: BLE001
            click.secho(f"Unexpected error: {exc}", fg="red", err=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
