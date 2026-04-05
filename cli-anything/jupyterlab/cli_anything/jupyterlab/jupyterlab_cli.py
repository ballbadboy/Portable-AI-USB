"""
cli_anything.jupyterlab.jupyterlab_cli
=======================================

Full Click CLI for the JupyterLab harness.

Entry-point: ``cli-anything-jupyterlab``

Command groups
--------------
kernel   - list, start, stop, specs, info, interrupt, restart
notebook - list, create, read, run, export, info, delete
server   - status, version
session  - list, status, delete

Special commands
----------------
repl     - Interactive REPL against a live kernel (requires websocket-client)

Global options (usable before any sub-command)
----------------------------------------------
--json           Output raw JSON instead of formatted tables
--host TEXT      Jupyter server URL  [default: http://localhost:8888]
--token TEXT     Jupyter auth token  [env var: JUPYTER_TOKEN]
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style

from cli_anything.jupyterlab.core import CliContext, error_exit, make_backend, pass_cli_ctx
from cli_anything.jupyterlab.utils.jupyter_backend import JupyterBackend, JupyterBackendError

# ---------------------------------------------------------------------------
# Shared style for prompt_toolkit REPL
# ---------------------------------------------------------------------------

_REPL_STYLE = Style.from_dict(
    {
        "prompt": "#00aaff bold",
        "": "#ffffff",
    }
)

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _print_json(obj: Any) -> None:
    click.echo(json.dumps(obj, indent=2, default=str))


def _table_row(cols: List[str], widths: List[int]) -> str:
    return "  ".join(str(c).ljust(w) for c, w in zip(cols, widths))


def _print_table(headers: List[str], rows: List[List[str]]) -> None:
    widths = [max(len(h), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    click.secho(_table_row(headers, widths), fg="bright_cyan", bold=True)
    click.echo("-" * sum(w + 2 for w in widths))
    for row in rows:
        click.echo(_table_row(row, widths))


def _truncate(s: str, n: int = 40) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


# ---------------------------------------------------------------------------
# Root command group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--json", "use_json", is_flag=True, default=False, help="Output raw JSON.")
@click.option(
    "--host",
    default="http://localhost:8888",
    show_default=True,
    envvar="JUPYTER_HOST",
    help="Jupyter server base URL.",
)
@click.option(
    "--token",
    default="",
    envvar="JUPYTER_TOKEN",
    help="Jupyter auth token (or set JUPYTER_TOKEN env var).",
    show_default=False,
)
@click.pass_context
def cli(ctx: click.Context, use_json: bool, host: str, token: str) -> None:
    """CLI-Anything harness for JupyterLab.

    Controls a running Jupyter server via its REST API.

    \b
    Environment variables:
      JUPYTER_HOST   - Server URL (overridden by --host)
      JUPYTER_TOKEN  - Auth token (overridden by --token)

    \b
    Examples:
      cli-anything-jupyterlab --token mytoken kernel list
      cli-anything-jupyterlab --json notebook list
      cli-anything-jupyterlab repl --kernel python3
    """
    ctx.ensure_object(dict)
    backend = make_backend(host, token)
    ctx.obj = CliContext(backend=backend, use_json=use_json)


# ---------------------------------------------------------------------------
# Helper: get CliContext safely
# ---------------------------------------------------------------------------


def _ctx_backend(ctx_obj: CliContext) -> JupyterBackend:
    return ctx_obj.backend


# ---------------------------------------------------------------------------
# Group: kernel
# ---------------------------------------------------------------------------


@cli.group()
@pass_cli_ctx
def kernel(ctx: CliContext) -> None:
    """Manage Jupyter kernels (list, start, stop, specs)."""


@kernel.command("list")
@pass_cli_ctx
def kernel_list(ctx: CliContext) -> None:
    """List all running kernels."""
    try:
        kernels = ctx.backend.list_kernels()
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(kernels)
        return

    if not kernels:
        click.echo("No kernels are currently running.")
        return

    rows = [
        [
            k.get("id", "")[:12],
            k.get("name", ""),
            k.get("execution_state", ""),
            str(k.get("connections", 0)),
            _truncate(k.get("last_activity", ""), 30),
        ]
        for k in kernels
    ]
    _print_table(["ID (short)", "Name", "State", "Conns", "Last Activity"], rows)


@kernel.command("start")
@click.argument("name", default="python3")
@pass_cli_ctx
def kernel_start(ctx: CliContext, name: str) -> None:
    """Start a new kernel with kernel-spec NAME (default: python3)."""
    try:
        k = ctx.backend.start_kernel(name=name)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(k)
        return

    click.secho(f"Kernel started.", fg="green")
    click.echo(f"  ID   : {k.get('id')}")
    click.echo(f"  Name : {k.get('name')}")


@kernel.command("stop")
@click.argument("kernel_id")
@pass_cli_ctx
def kernel_stop(ctx: CliContext, kernel_id: str) -> None:
    """Stop (terminate) the kernel with KERNEL_ID."""
    try:
        ctx.backend.stop_kernel(kernel_id)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json({"stopped": kernel_id})
        return
    click.secho(f"Kernel {kernel_id} stopped.", fg="yellow")


@kernel.command("specs")
@pass_cli_ctx
def kernel_specs(ctx: CliContext) -> None:
    """List all available kernel specifications."""
    try:
        specs_data = ctx.backend.list_kernel_specs()
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(specs_data)
        return

    default = specs_data.get("default", "")
    kernelspecs: Dict[str, Any] = specs_data.get("kernelspecs", {})
    rows = []
    for name, spec in kernelspecs.items():
        resources = spec.get("spec", {})
        display = resources.get("display_name", name)
        lang = resources.get("language", "")
        mark = "*" if name == default else " "
        rows.append([mark, name, display, lang])

    _print_table(["Def", "Name", "Display Name", "Language"], rows)
    click.echo(f"\n* = default kernel ({default})")


@kernel.command("info")
@click.argument("kernel_id")
@pass_cli_ctx
def kernel_info(ctx: CliContext, kernel_id: str) -> None:
    """Show detailed info for KERNEL_ID."""
    try:
        k = ctx.backend.get_kernel(kernel_id)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(k)
        return

    for key, val in k.items():
        click.echo(f"  {key:<20}: {val}")


@kernel.command("interrupt")
@click.argument("kernel_id")
@pass_cli_ctx
def kernel_interrupt(ctx: CliContext, kernel_id: str) -> None:
    """Interrupt (Ctrl-C) the kernel with KERNEL_ID."""
    try:
        ctx.backend.interrupt_kernel(kernel_id)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json({"interrupted": kernel_id})
        return
    click.secho(f"Kernel {kernel_id} interrupted.", fg="yellow")


@kernel.command("restart")
@click.argument("kernel_id")
@pass_cli_ctx
def kernel_restart(ctx: CliContext, kernel_id: str) -> None:
    """Restart the kernel with KERNEL_ID."""
    try:
        k = ctx.backend.restart_kernel(kernel_id)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(k)
        return
    click.secho(f"Kernel {kernel_id} restarted.", fg="green")


# ---------------------------------------------------------------------------
# Group: notebook
# ---------------------------------------------------------------------------


@cli.group()
@pass_cli_ctx
def notebook(ctx: CliContext) -> None:
    """Manage Jupyter notebooks (list, create, run, export)."""


@notebook.command("list")
@click.argument("path", default="")
@pass_cli_ctx
def notebook_list(ctx: CliContext, path: str) -> None:
    """List notebooks at server-side PATH (default: root directory)."""
    try:
        notebooks = ctx.backend.list_notebooks(path=path)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(notebooks)
        return

    if not notebooks:
        click.echo(f"No notebooks found at path: '{path or '/'}'")
        return

    rows = [
        [
            nb.get("name", ""),
            nb.get("path", ""),
            _truncate(nb.get("last_modified", ""), 25),
            str(nb.get("size", "")),
        ]
        for nb in notebooks
    ]
    _print_table(["Name", "Path", "Last Modified", "Size"], rows)


@notebook.command("create")
@click.argument("path")
@click.option("--kernel", default="python3", show_default=True, help="Kernel spec name.")
@pass_cli_ctx
def notebook_create(ctx: CliContext, path: str, kernel: str) -> None:
    """Create a new empty notebook at server-side PATH."""
    try:
        nb = ctx.backend.create_notebook(path=path, kernel_name=kernel)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(nb)
        return

    click.secho(f"Notebook created: {nb.get('path')}", fg="green")


@notebook.command("info")
@click.argument("path")
@pass_cli_ctx
def notebook_info(ctx: CliContext, path: str) -> None:
    """Show metadata for the notebook at server-side PATH."""
    try:
        nb = ctx.backend.read_notebook(path)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        # Omit full cell content for readability; show metadata only.
        info = {k: v for k, v in nb.items() if k != "content"}
        content = nb.get("content", {})
        info["cell_count"] = len(content.get("cells", []))
        info["kernel"] = content.get("metadata", {}).get("kernelspec", {})
        _print_json(info)
        return

    content = nb.get("content", {})
    cells = content.get("cells", [])
    ks = content.get("metadata", {}).get("kernelspec", {})
    click.echo(f"  Path         : {nb.get('path')}")
    click.echo(f"  Name         : {nb.get('name')}")
    click.echo(f"  Last Modified: {nb.get('last_modified')}")
    click.echo(f"  Size         : {nb.get('size')} bytes")
    click.echo(f"  Cells        : {len(cells)} total")
    code_cells = sum(1 for c in cells if c.get("cell_type") == "code")
    click.echo(f"  Code cells   : {code_cells}")
    click.echo(f"  Kernel       : {ks.get('display_name', ks.get('name', 'unknown'))}")
    click.echo(f"  nbformat     : {content.get('nbformat')}.{content.get('nbformat_minor')}")


@notebook.command("run")
@click.argument("path")
@click.option("--kernel", default="python3", show_default=True, help="Kernel spec to use.")
@click.option("--timeout", default=120, show_default=True, help="Per-cell timeout in seconds.")
@pass_cli_ctx
def notebook_run(ctx: CliContext, path: str, kernel: str, timeout: int) -> None:
    """Execute all code cells in the notebook at server-side PATH.

    A temporary kernel is started and stopped automatically.
    Execution stops on the first cell error.
    """
    click.echo(f"Running notebook: {path} (kernel={kernel}) ...")
    try:
        results = ctx.backend.run_notebook(path, kernel_name=kernel, cell_timeout=timeout)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(results)
        return

    for i, result in enumerate(results, 1):
        status = result.get("status", "ok")
        colour = "green" if status == "ok" else "red"
        click.secho(f"\n--- Cell {i} [{status}] ---", fg=colour)
        text = result.get("text", "").strip()
        if text:
            click.echo(text)
        if status == "error":
            err = result.get("error") or {}
            click.secho(f"{err.get('ename')}: {err.get('evalue')}", fg="red")

    total = len(results)
    errors = sum(1 for r in results if r.get("status") == "error")
    colour = "red" if errors else "green"
    click.secho(f"\n{total} cells executed, {errors} error(s).", fg=colour)


@notebook.command("export")
@click.argument("local_path")
@click.option(
    "--format",
    "fmt",
    default="script",
    show_default=True,
    type=click.Choice(["script", "html", "pdf", "markdown", "rst", "latex", "slides"], case_sensitive=False),
    help="nbconvert export format.",
)
@click.option("--output-dir", default=None, help="Directory to write the output file.")
@click.option("--execute", is_flag=True, default=False, help="Execute the notebook before converting.")
@pass_cli_ctx
def notebook_export(ctx: CliContext, local_path: str, fmt: str, output_dir: Optional[str], execute: bool) -> None:
    """Export a local notebook at LOCAL_PATH using nbconvert.

    \b
    Formats:
      script    -> .py
      html      -> .html
      pdf       -> .pdf  (requires LaTeX)
      markdown  -> .md
      rst       -> .rst
      latex     -> .tex
      slides    -> .html (reveal.js)
    """
    try:
        proc = ctx.backend.export_notebook(local_path, fmt=fmt, output_dir=output_dir, execute=execute)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(
            {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
        return

    click.secho(f"Export successful (format={fmt}).", fg="green")
    if proc.stdout.strip():
        click.echo(proc.stdout.strip())


@notebook.command("delete")
@click.argument("path")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation prompt.")
@pass_cli_ctx
def notebook_delete(ctx: CliContext, path: str, yes: bool) -> None:
    """Delete the notebook at server-side PATH."""
    if not yes:
        click.confirm(f"Delete notebook '{path}'?", abort=True)
    try:
        ctx.backend.delete_file(path)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json({"deleted": path})
        return
    click.secho(f"Deleted: {path}", fg="yellow")


# ---------------------------------------------------------------------------
# Group: server
# ---------------------------------------------------------------------------


@cli.group()
@pass_cli_ctx
def server(ctx: CliContext) -> None:
    """Query Jupyter server status and version information."""


@server.command("status")
@pass_cli_ctx
def server_status(ctx: CliContext) -> None:
    """Show server status (uptime, active kernels, connections)."""
    try:
        info = ctx.backend.server_info()
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(info)
        return

    click.secho("Jupyter Server Status", fg="bright_cyan", bold=True)
    click.echo("-" * 30)
    for key, val in info.items():
        click.echo(f"  {key:<20}: {val}")


@server.command("version")
@pass_cli_ctx
def server_version(ctx: CliContext) -> None:
    """Print just the Jupyter Server version string."""
    try:
        version = ctx.backend.server_version()
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json({"version": version})
        return
    click.echo(version)


# ---------------------------------------------------------------------------
# Group: session
# ---------------------------------------------------------------------------


@cli.group()
@pass_cli_ctx
def session(ctx: CliContext) -> None:
    """Manage Jupyter sessions (notebook <-> kernel associations)."""


@session.command("list")
@pass_cli_ctx
def session_list(ctx: CliContext) -> None:
    """List all active sessions."""
    try:
        sessions = ctx.backend.list_sessions()
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(sessions)
        return

    if not sessions:
        click.echo("No active sessions.")
        return

    rows = [
        [
            s.get("id", "")[:12],
            _truncate(s.get("path", ""), 35),
            s.get("type", ""),
            s.get("kernel", {}).get("id", "")[:12],
            s.get("kernel", {}).get("name", ""),
            s.get("kernel", {}).get("execution_state", ""),
        ]
        for s in sessions
    ]
    _print_table(
        ["Session ID", "Path", "Type", "Kernel ID", "Kernel Name", "State"],
        rows,
    )


@session.command("status")
@click.argument("session_id")
@pass_cli_ctx
def session_status(ctx: CliContext, session_id: str) -> None:
    """Show detailed status of SESSION_ID."""
    try:
        s = ctx.backend.get_session(session_id)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json(s)
        return

    click.echo(f"  Session ID  : {s.get('id')}")
    click.echo(f"  Path        : {s.get('path')}")
    click.echo(f"  Name        : {s.get('name')}")
    click.echo(f"  Type        : {s.get('type')}")
    kernel = s.get("kernel", {})
    click.echo(f"  Kernel ID   : {kernel.get('id')}")
    click.echo(f"  Kernel Name : {kernel.get('name')}")
    click.echo(f"  Kernel State: {kernel.get('execution_state')}")


@session.command("delete")
@click.argument("session_id")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation.")
@pass_cli_ctx
def session_delete(ctx: CliContext, session_id: str, yes: bool) -> None:
    """Delete (and stop the kernel of) SESSION_ID."""
    if not yes:
        click.confirm(f"Delete session '{session_id}'?", abort=True)
    try:
        ctx.backend.delete_session(session_id)
    except JupyterBackendError as exc:
        error_exit(str(exc), ctx.use_json)

    if ctx.use_json:
        _print_json({"deleted": session_id})
        return
    click.secho(f"Session {session_id} deleted.", fg="yellow")


# ---------------------------------------------------------------------------
# REPL mode
# ---------------------------------------------------------------------------


@cli.command("repl")
@click.option(
    "--kernel-id",
    default=None,
    help="Attach to an existing kernel by ID. If omitted, a new kernel is started.",
)
@click.option("--kernel", "kernel_name", default="python3", show_default=True, help="Kernel spec to start.")
@click.option("--timeout", default=60, show_default=True, help="Per-cell execution timeout in seconds.")
@pass_cli_ctx
def repl(ctx: CliContext, kernel_id: Optional[str], kernel_name: str, timeout: int) -> None:
    """Interactive REPL - execute code against a live Jupyter kernel.

    \b
    Special commands:
      %kernels   - list running kernels
      %restart   - restart the current kernel
      %exit      - quit the REPL  (also: exit, quit, Ctrl-D)

    Multi-line input: end a line with \\ to continue on the next line.
    """
    backend = ctx.backend
    started_kernel = False

    if kernel_id is None:
        try:
            k = backend.start_kernel(name=kernel_name)
            kernel_id = k["id"]
            started_kernel = True
            click.secho(f"Started kernel: {kernel_id} ({kernel_name})", fg="green")
        except JupyterBackendError as exc:
            error_exit(str(exc), ctx.use_json)
    else:
        click.secho(f"Attaching to kernel: {kernel_id}", fg="cyan")

    click.echo("Type Python code to execute.  %exit or Ctrl-D to quit.\n")

    # Try to use Pygments for syntax highlighting; fall back gracefully.
    lexer = None
    try:
        from pygments.lexers import PythonLexer  # type: ignore[import]

        lexer = PygmentsLexer(PythonLexer)
    except ImportError:
        pass

    history = InMemoryHistory()
    session_pt: PromptSession = PromptSession(
        history=history,
        lexer=lexer,
        style=_REPL_STYLE,
        multiline=False,
    )

    def _run_code(code: str) -> None:
        try:
            result = backend.execute_cell(kernel_id, code, timeout=timeout)
        except JupyterBackendError as exc:
            click.secho(f"Execution error: {exc}", fg="red")
            return

        text = result.get("text", "").rstrip()
        status = result.get("status", "ok")
        if text:
            click.echo(text)
        if status == "error":
            err = result.get("error") or {}
            click.secho(f"{err.get('ename')}: {err.get('evalue')}", fg="red")

    try:
        while True:
            try:
                prompt_text = [("class:prompt", "In  >>> ")]
                line: str = session_pt.prompt(prompt_text)
            except EOFError:
                break
            except KeyboardInterrupt:
                click.echo("KeyboardInterrupt (use %exit to quit)")
                continue

            line = line.strip()
            if not line:
                continue

            # Special meta-commands
            if line in ("%exit", "exit", "quit", "exit()", "quit()"):
                break
            if line == "%kernels":
                try:
                    kernels = backend.list_kernels()
                    _print_json(kernels)
                except JupyterBackendError as exc:
                    click.secho(str(exc), fg="red")
                continue
            if line == "%restart":
                try:
                    backend.restart_kernel(kernel_id)
                    click.secho("Kernel restarted.", fg="yellow")
                except JupyterBackendError as exc:
                    click.secho(str(exc), fg="red")
                continue

            # Multi-line continuation (trailing backslash)
            code_lines = [line]
            while line.endswith("\\"):
                code_lines[-1] = code_lines[-1][:-1]  # strip backslash
                try:
                    cont: str = session_pt.prompt([("class:prompt", "     ... ")])
                    code_lines.append(cont)
                    line = cont
                except (EOFError, KeyboardInterrupt):
                    break

            _run_code("\n".join(code_lines))

    finally:
        if started_kernel and kernel_id:
            try:
                backend.stop_kernel(kernel_id)
                click.secho(f"\nKernel {kernel_id} stopped.", fg="yellow")
            except JupyterBackendError:
                pass


# ---------------------------------------------------------------------------
# Package entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    """Package entry-point invoked by ``cli-anything-jupyterlab``."""
    cli(auto_envvar_prefix="JUPYTER")


if __name__ == "__main__":
    main()
