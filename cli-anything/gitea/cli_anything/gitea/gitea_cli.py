"""
gitea_cli
~~~~~~~~~

Full-featured Click CLI for Gitea with an optional REPL mode.

Usage examples
--------------
    cli-anything-gitea --host http://localhost:3000 --token mytoken repo list myuser
    cli-anything-gitea --json repo info myuser myrepo
    cli-anything-gitea repl
    GITEA_HOST=http://localhost:3000 GITEA_TOKEN=mytoken cli-anything-gitea user info
"""

from __future__ import annotations

import json
import os
import sys
import shlex
from typing import Any

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from cli_anything.gitea.utils.gitea_backend import GiteaBackend, GiteaAPIError


# ---------------------------------------------------------------------------
# Shared context object
# ---------------------------------------------------------------------------


class AppContext:
    """Passed via Click's obj mechanism to every command."""

    def __init__(self, host: str, token: str, as_json: bool) -> None:
        self.as_json = as_json
        self.backend = GiteaBackend(base_url=host, token=token)

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def out(self, data: Any, title: str = "") -> None:
        """Print *data* as JSON or human-readable text."""
        if self.as_json:
            click.echo(json.dumps(data, indent=2, default=str))
            return
        if title:
            click.secho(f"\n{title}", fg="cyan", bold=True)
        _pretty_print(data)

    def success(self, msg: str) -> None:
        if self.as_json:
            click.echo(json.dumps({"status": "ok", "message": msg}))
        else:
            click.secho(f"  {msg}", fg="green")

    def error(self, msg: str) -> None:
        if self.as_json:
            click.echo(json.dumps({"status": "error", "message": msg}), err=True)
        else:
            click.secho(f"  ERROR: {msg}", fg="red", err=True)


# ---------------------------------------------------------------------------
# Internal pretty-printer
# ---------------------------------------------------------------------------


def _pretty_print(data: Any, indent: int = 0) -> None:
    pad = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                click.echo(f"{pad}{click.style(k, bold=True)}:")
                _pretty_print(v, indent + 1)
            else:
                click.echo(f"{pad}{click.style(k, bold=True)}: {v}")
    elif isinstance(data, list):
        if not data:
            click.echo(f"{pad}(empty)")
            return
        for i, item in enumerate(data):
            click.echo(f"{pad}{click.style(f'[{i}]', fg='yellow')}")
            _pretty_print(item, indent + 1)
    else:
        click.echo(f"{pad}{data}")


# ---------------------------------------------------------------------------
# Error handler decorator
# ---------------------------------------------------------------------------


def handle_api_errors(fn):
    """Decorator: catch GiteaAPIError and exit cleanly."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        ctx_obj: AppContext | None = None
        # Pull AppContext from Click context if available
        for a in args:
            if isinstance(a, AppContext):
                ctx_obj = a
                break
        try:
            return fn(*args, **kwargs)
        except GiteaAPIError as exc:
            msg = f"API error {exc.status_code}: {exc.message}"
            if ctx_obj:
                ctx_obj.error(msg)
            else:
                click.secho(f"  ERROR: {msg}", fg="red", err=True)
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if ctx_obj:
                ctx_obj.error(msg)
            else:
                click.secho(f"  ERROR: {msg}", fg="red", err=True)
            sys.exit(1)

    return wrapper


# ---------------------------------------------------------------------------
# Root command group
# ---------------------------------------------------------------------------


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120},
    invoke_without_command=True,
)
@click.option(
    "--host",
    envvar="GITEA_HOST",
    default="http://localhost:3000",
    show_default=True,
    help="Base URL of the Gitea instance.",
)
@click.option(
    "--token",
    envvar="GITEA_TOKEN",
    default="",
    help="Gitea personal access token.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    envvar="GITEA_JSON",
    help="Output results as JSON.",
)
@click.pass_context
def cli(ctx: click.Context, host: str, token: str, as_json: bool) -> None:
    """CLI-Anything harness for Gitea self-hosted Git service.

    Set GITEA_HOST and GITEA_TOKEN environment variables to avoid repeating
    options on every invocation.

    Run `cli-anything-gitea repl` to enter an interactive REPL.
    """
    ctx.ensure_object(dict)
    ctx.obj = AppContext(host=host, token=token, as_json=as_json)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ===========================================================================
# Group: repo
# ===========================================================================


@cli.group()
@click.pass_obj
def repo(obj: AppContext) -> None:
    """Repository operations."""


@repo.command("list")
@click.argument("owner")
@click.pass_obj
@handle_api_errors
def repo_list(obj: AppContext, owner: str) -> None:
    """List repositories owned by OWNER."""
    repos = obj.backend.list_repos(owner)
    if obj.as_json:
        obj.out(repos)
        return
    click.secho(f"\nRepositories for {owner} ({len(repos)} total)", fg="cyan", bold=True)
    for r in repos:
        private_flag = click.style("[private]", fg="yellow") if r.get("private") else ""
        stars = r.get("stars_count", 0)
        click.echo(
            f"  {click.style(r['name'], bold=True)}  {private_flag}  "
            f"stars={stars}  {r.get('description', '')}"
        )


@repo.command("create")
@click.argument("name")
@click.option("-d", "--description", default="", help="Repository description.")
@click.option("--private", is_flag=True, default=False, help="Make the repository private.")
@click.option("--auto-init", is_flag=True, default=False, help="Auto-initialise with README.")
@click.option("--branch", default="main", show_default=True, help="Default branch name.")
@click.pass_obj
@handle_api_errors
def repo_create(
    obj: AppContext,
    name: str,
    description: str,
    private: bool,
    auto_init: bool,
    branch: str,
) -> None:
    """Create a new repository."""
    result = obj.backend.create_repo(
        name=name,
        description=description,
        private=private,
        auto_init=auto_init,
        default_branch=branch,
    )
    obj.out(result, title=f"Repository '{name}' created")


@repo.command("delete")
@click.argument("owner")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
@handle_api_errors
def repo_delete(obj: AppContext, owner: str, name: str, yes: bool) -> None:
    """Permanently delete OWNER/NAME."""
    if not yes:
        click.confirm(
            click.style(f"  Permanently delete {owner}/{name}?", fg="red"),
            abort=True,
        )
    obj.backend.delete_repo(owner, name)
    obj.success(f"Deleted {owner}/{name}")


@repo.command("info")
@click.argument("owner")
@click.argument("name")
@click.pass_obj
@handle_api_errors
def repo_info(obj: AppContext, owner: str, name: str) -> None:
    """Show metadata for OWNER/NAME."""
    data = obj.backend.get_repo(owner, name)
    obj.out(data, title=f"{owner}/{name}")


@repo.command("clone-url")
@click.argument("owner")
@click.argument("name")
@click.option("--ssh", is_flag=True, help="Show SSH clone URL.")
@click.pass_obj
@handle_api_errors
def repo_clone_url(obj: AppContext, owner: str, name: str, ssh: bool) -> None:
    """Print the clone URL for OWNER/NAME."""
    data = obj.backend.get_repo(owner, name)
    url = data.get("ssh_url") if ssh else data.get("clone_url")
    if obj.as_json:
        obj.out({"clone_url": url})
    else:
        click.echo(url)


@repo.command("fork")
@click.argument("owner")
@click.argument("name")
@click.option("--org", default="", help="Fork into this organisation instead of your user.")
@click.pass_obj
@handle_api_errors
def repo_fork(obj: AppContext, owner: str, name: str, org: str) -> None:
    """Fork OWNER/NAME."""
    result = obj.backend.fork_repo(owner, name, organization=org)
    obj.out(result, title=f"Forked {owner}/{name}")


@repo.command("search")
@click.argument("query")
@click.option("--limit", default=20, show_default=True, help="Max results.")
@click.pass_obj
@handle_api_errors
def repo_search(obj: AppContext, query: str, limit: int) -> None:
    """Search repositories by QUERY."""
    results = obj.backend.search_repos(query, limit=limit)
    if obj.as_json:
        obj.out(results)
        return
    click.secho(f"\nSearch results for '{query}' ({len(results)} found)", fg="cyan", bold=True)
    for r in results:
        click.echo(
            f"  {click.style(r['full_name'], bold=True)}  "
            f"{r.get('description', '')}"
        )


# ===========================================================================
# Group: issue
# ===========================================================================


@cli.group()
@click.pass_obj
def issue(obj: AppContext) -> None:
    """Issue tracker operations."""


@issue.command("list")
@click.argument("owner")
@click.argument("repo_name", metavar="REPO")
@click.option(
    "--state",
    default="open",
    type=click.Choice(["open", "closed", "all"]),
    show_default=True,
    help="Filter by issue state.",
)
@click.option("--limit", default=50, show_default=True, help="Max issues per page.")
@click.pass_obj
@handle_api_errors
def issue_list(obj: AppContext, owner: str, repo_name: str, state: str, limit: int) -> None:
    """List issues for OWNER/REPO."""
    issues = obj.backend.list_issues(owner, repo_name, state=state, limit=limit)
    if obj.as_json:
        obj.out(issues)
        return
    click.secho(
        f"\nIssues for {owner}/{repo_name} [{state}] ({len(issues)} total)",
        fg="cyan",
        bold=True,
    )
    for iss in issues:
        num = click.style(f"#{iss['number']}", fg="yellow")
        title = iss.get("title", "")
        user = iss.get("user", {}).get("login", "?")
        click.echo(f"  {num}  {title}  (by {user})")


@issue.command("create")
@click.argument("owner")
@click.argument("repo_name", metavar="REPO")
@click.option("-t", "--title", required=True, help="Issue title.")
@click.option("-b", "--body", default="", help="Issue body / description.")
@click.pass_obj
@handle_api_errors
def issue_create(obj: AppContext, owner: str, repo_name: str, title: str, body: str) -> None:
    """Open a new issue in OWNER/REPO."""
    result = obj.backend.create_issue(owner, repo_name, title=title, body=body)
    obj.out(result, title=f"Issue #{result.get('number')} created")


@issue.command("close")
@click.argument("owner")
@click.argument("repo_name", metavar="REPO")
@click.argument("issue_id", type=int)
@click.pass_obj
@handle_api_errors
def issue_close(obj: AppContext, owner: str, repo_name: str, issue_id: int) -> None:
    """Close issue ISSUE_ID in OWNER/REPO."""
    result = obj.backend.close_issue(owner, repo_name, issue_id)
    obj.out(result, title=f"Issue #{issue_id} closed")


@issue.command("get")
@click.argument("owner")
@click.argument("repo_name", metavar="REPO")
@click.argument("issue_id", type=int)
@click.pass_obj
@handle_api_errors
def issue_get(obj: AppContext, owner: str, repo_name: str, issue_id: int) -> None:
    """Show details for issue ISSUE_ID in OWNER/REPO."""
    data = obj.backend.get_issue(owner, repo_name, issue_id)
    obj.out(data, title=f"Issue #{issue_id} in {owner}/{repo_name}")


# ===========================================================================
# Group: user
# ===========================================================================


@cli.group()
@click.pass_obj
def user(obj: AppContext) -> None:
    """User account operations."""


@user.command("info")
@click.argument("username", required=False, default=None)
@click.pass_obj
@handle_api_errors
def user_info(obj: AppContext, username: str | None) -> None:
    """Show the authenticated user's profile, or USERNAME if provided."""
    if username:
        data = obj.backend.get_user_by_name(username)
    else:
        data = obj.backend.get_user()
    obj.out(data, title="User Profile")


@user.command("list-repos")
@click.argument("username", required=False, default=None)
@click.pass_obj
@handle_api_errors
def user_list_repos(obj: AppContext, username: str | None) -> None:
    """List repos for USERNAME (defaults to authenticated user)."""
    if not username:
        me = obj.backend.get_user()
        username = me.get("login", "")
    repos = obj.backend.list_repos(username)
    if obj.as_json:
        obj.out(repos)
        return
    click.secho(f"\nRepositories for {username} ({len(repos)} total)", fg="cyan", bold=True)
    for r in repos:
        click.echo(f"  {click.style(r['name'], bold=True)}  {r.get('description', '')}")


@user.command("orgs")
@click.pass_obj
@handle_api_errors
def user_orgs(obj: AppContext) -> None:
    """List organisations the authenticated user belongs to."""
    orgs = obj.backend.list_orgs()
    obj.out(orgs, title="Organisations")


# ===========================================================================
# Group: file
# ===========================================================================


@cli.group()
@click.pass_obj
def file(obj: AppContext) -> None:
    """File and directory operations."""


@file.command("get")
@click.argument("owner")
@click.argument("repo_name", metavar="REPO")
@click.argument("path")
@click.option("--branch", default="", help="Branch/tag/commit (default: repo default branch).")
@click.option("--raw", is_flag=True, help="Output raw file content only.")
@click.pass_obj
@handle_api_errors
def file_get(
    obj: AppContext,
    owner: str,
    repo_name: str,
    path: str,
    branch: str,
    raw: bool,
) -> None:
    """Get a file from OWNER/REPO at PATH."""
    data = obj.backend.get_file(owner, repo_name, path, branch=branch)
    if raw:
        click.echo(data.get("decoded_content", ""))
        return
    obj.out(data, title=f"{path} in {owner}/{repo_name}")


@file.command("list")
@click.argument("owner")
@click.argument("repo_name", metavar="REPO")
@click.argument("path", required=False, default="")
@click.option("--branch", default="", help="Branch/tag/commit (default: repo default branch).")
@click.pass_obj
@handle_api_errors
def file_list(
    obj: AppContext,
    owner: str,
    repo_name: str,
    path: str,
    branch: str,
) -> None:
    """List directory contents in OWNER/REPO at PATH."""
    items = obj.backend.list_contents(owner, repo_name, path=path, branch=branch)
    if obj.as_json:
        obj.out(items)
        return
    display_path = path or "/"
    click.secho(f"\nContents of {owner}/{repo_name}:{display_path}", fg="cyan", bold=True)
    for item in items:
        kind = item.get("type", "?")
        icon = "d" if kind == "dir" else "f"
        size = item.get("size", "")
        name = item.get("name", item.get("path", "?"))
        click.echo(f"  [{icon}]  {click.style(name, bold=(kind == 'dir'))}  {size}")


# ===========================================================================
# Group: server
# ===========================================================================


@cli.group()
@click.pass_obj
def server(obj: AppContext) -> None:
    """Server meta-information."""


@server.command("status")
@click.pass_obj
@handle_api_errors
def server_status(obj: AppContext) -> None:
    """Check whether the Gitea server is reachable."""
    data = obj.backend.get_server_status()
    if obj.as_json:
        obj.out(data)
        return
    reachable = data.get("reachable", False)
    version = data.get("version", "?")
    colour = "green" if reachable else "red"
    status_word = "ONLINE" if reachable else "OFFLINE"
    click.secho(f"\n  Server: {click.style(status_word, fg=colour, bold=True)}  (v{version})")


@server.command("version")
@click.pass_obj
@handle_api_errors
def server_version(obj: AppContext) -> None:
    """Print the Gitea server version."""
    data = obj.backend.get_version()
    obj.out(data, title="Server Version")


# ===========================================================================
# REPL
# ===========================================================================

_REPL_COMMANDS = [
    "repo list", "repo create", "repo delete", "repo info", "repo clone-url", "repo fork",
    "repo search",
    "issue list", "issue create", "issue close", "issue get",
    "user info", "user list-repos", "user orgs",
    "file get", "file list",
    "server status", "server version",
    "help", "exit", "quit",
]


def _repl_completer() -> WordCompleter:
    return WordCompleter(_REPL_COMMANDS, ignore_case=True, sentence=True)


@cli.command("repl")
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Start an interactive REPL for the Gitea CLI.

    Type `help` for available commands, `exit` or `quit` to leave.
    The REPL inherits --host, --token and --json flags from the parent.
    """
    obj: AppContext = ctx.obj
    session: PromptSession = PromptSession(
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
        completer=_repl_completer(),
    )

    host = obj.backend.base_url
    click.secho(f"\n  Gitea REPL  ({host})", fg="cyan", bold=True)
    click.echo("  Type `help` for commands, `exit` to quit.\n")

    while True:
        try:
            raw = session.prompt("gitea> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\n  Bye.")
            break

        if not raw:
            continue
        if raw.lower() in ("exit", "quit"):
            click.echo("  Bye.")
            break
        if raw.lower() in ("help", "?"):
            click.echo("\n  Available command groups and commands:")
            for cmd in _REPL_COMMANDS:
                if cmd not in ("help", "exit", "quit"):
                    click.echo(f"    {cmd}")
            click.echo()
            continue

        # Re-invoke the CLI root with the accumulated args
        try:
            args = shlex.split(raw)
        except ValueError as exc:
            click.secho(f"  Parse error: {exc}", fg="red")
            continue

        try:
            # standalone_mode=False prevents SystemExit on --help
            cli.main(
                args=args,
                obj=obj,
                standalone_mode=False,
                parent=ctx,
            )
        except click.ClickException as exc:
            click.secho(f"  Error: {exc.format_message()}", fg="red")
        except click.Abort:
            click.echo("  Aborted.")
        except SystemExit:
            pass
        except GiteaAPIError as exc:
            click.secho(f"  API error {exc.status_code}: {exc.message}", fg="red")
        except Exception as exc:  # noqa: BLE001
            click.secho(f"  Error: {exc}", fg="red")

        click.echo()
