# cli-anything-gitea — Skill Reference

A complete CLI harness for [Gitea](https://gitea.io) self-hosted Git service,
built on the Gitea REST API v1.

---

## Installation

```bash
pip install -e /path/to/cli-anything/gitea
# or, once published:
pip install cli-anything-gitea
```

---

## Configuration

| Method | Variable | Description |
|--------|----------|-------------|
| Env var | `GITEA_HOST` | Base URL, e.g. `http://localhost:3000` |
| Env var | `GITEA_TOKEN` | Personal access token |
| Env var | `GITEA_JSON` | Set to `1` for JSON output |
| CLI flag | `--host` | Override host per invocation |
| CLI flag | `--token` | Override token per invocation |
| CLI flag | `--json` | Output raw JSON |

Generate a token at **Gitea → Settings → Applications → Generate Token**
(requires `repo`, `issue`, `user` scopes).

---

## Quick Start

```bash
export GITEA_HOST=http://localhost:3000
export GITEA_TOKEN=your_token_here

cli-anything-gitea user info
cli-anything-gitea repo list myuser
cli-anything-gitea repl
```

---

## Command Reference

### Global Options

```
cli-anything-gitea [--host URL] [--token TOKEN] [--json] COMMAND [ARGS...]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `http://localhost:3000` | Gitea instance URL |
| `--token` | *(empty)* | API token |
| `--json` | off | Emit raw JSON instead of formatted output |

---

### `repo` — Repository Operations

| Command | Arguments | Description |
|---------|-----------|-------------|
| `repo list OWNER` | `OWNER` — username or org | List all repos for owner |
| `repo create NAME` | `NAME` + options | Create a new repo under authenticated user |
| `repo delete OWNER NAME` | `--yes` to skip confirm | Permanently delete a repo |
| `repo info OWNER NAME` | | Show repo metadata |
| `repo clone-url OWNER NAME` | `--ssh` for SSH URL | Print clone URL |
| `repo fork OWNER NAME` | `--org ORG` | Fork into user or org |
| `repo search QUERY` | `--limit N` | Full-text repo search |

**Examples**

```bash
# List repos
cli-anything-gitea repo list alice

# Create a private repo with a README
cli-anything-gitea repo create my-new-repo --private --auto-init -d "My project"

# Get clone URL
cli-anything-gitea repo clone-url alice awesome-lib

# Fork
cli-anything-gitea repo fork alice awesome-lib --org my-org

# Search
cli-anything-gitea --json repo search "kubernetes" --limit 5
```

---

### `issue` — Issue Tracker Operations

| Command | Arguments | Description |
|---------|-----------|-------------|
| `issue list OWNER REPO` | `--state open\|closed\|all` | List issues |
| `issue create OWNER REPO` | `-t TITLE -b BODY` | Open a new issue |
| `issue close OWNER REPO ID` | | Close an issue by number |
| `issue get OWNER REPO ID` | | Fetch a single issue |

**Examples**

```bash
cli-anything-gitea issue list alice myrepo --state open
cli-anything-gitea issue create alice myrepo -t "Bug: crash on startup" -b "Steps to reproduce..."
cli-anything-gitea issue close alice myrepo 42
cli-anything-gitea --json issue get alice myrepo 7
```

---

### `user` — User Account Operations

| Command | Arguments | Description |
|---------|-----------|-------------|
| `user info [USERNAME]` | optional username | Show user profile |
| `user list-repos [USERNAME]` | optional username | List user's repos |
| `user orgs` | | List authenticated user's orgs |

**Examples**

```bash
cli-anything-gitea user info
cli-anything-gitea user info alice
cli-anything-gitea user list-repos
cli-anything-gitea user orgs
```

---

### `file` — File & Directory Operations

| Command | Arguments | Description |
|---------|-----------|-------------|
| `file get OWNER REPO PATH` | `--branch`, `--raw` | Fetch a file; `--raw` prints content only |
| `file list OWNER REPO [PATH]` | `--branch` | List directory contents |

**Examples**

```bash
cli-anything-gitea file get alice myrepo README.md --raw
cli-anything-gitea file get alice myrepo src/main.py --branch develop
cli-anything-gitea file list alice myrepo src/
cli-anything-gitea --json file list alice myrepo
```

---

### `server` — Server Meta-Information

| Command | Description |
|---------|-------------|
| `server status` | Check reachability and version |
| `server version` | Print server version string |

**Examples**

```bash
cli-anything-gitea server status
cli-anything-gitea --json server version
```

---

### `repl` — Interactive REPL

```bash
cli-anything-gitea --host http://gitea.local --token mytoken repl
```

Inside the REPL, type any subcommand without the `cli-anything-gitea` prefix:

```
gitea> user info
gitea> repo list alice
gitea> issue create alice myrepo -t "Fix the typo"
gitea> help
gitea> exit
```

Features:
- Command history (up/down arrow)
- Tab completion for command names
- Auto-suggest from history
- Inherits `--host`, `--token`, and `--json` from the parent invocation

---

## GiteaBackend API (Python)

```python
from cli_anything.gitea.utils import GiteaBackend

backend = GiteaBackend(base_url="http://localhost:3000", token="mytoken")

# User
me = backend.get_user()

# Repos
repos = backend.list_repos("alice")
repo  = backend.get_repo("alice", "myrepo")
new   = backend.create_repo("my-project", description="...", private=True)
backend.delete_repo("alice", "old-repo")
fork  = backend.fork_repo("alice", "myrepo")

# Issues
issues = backend.list_issues("alice", "myrepo", state="open")
issue  = backend.create_issue("alice", "myrepo", title="Bug", body="...")
closed = backend.close_issue("alice", "myrepo", issue_id=5)

# Branches
branches = backend.list_branches("alice", "myrepo")

# Files
file_data = backend.get_file("alice", "myrepo", "README.md", branch="main")
print(file_data["decoded_content"])

contents = backend.list_contents("alice", "myrepo", path="src/")

# Search & Orgs
results = backend.search_repos("kubernetes")
orgs    = backend.list_orgs()
```

All methods raise `GiteaAPIError(status_code, message, url)` on API errors.

---

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or missing token |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g. repo already exists) |
| 422 | Validation error |

---

## Architecture

```
cli-anything/gitea/
├── setup.py                          # Package metadata & entry point
└── cli_anything/gitea/
    ├── __init__.py                   # Version declaration
    ├── __main__.py                   # python -m cli_anything.gitea support
    ├── gitea_cli.py                  # Click CLI (all groups & commands)
    ├── core/
    │   └── __init__.py
    ├── skills/
    │   └── SKILL.md                  # This file
    └── utils/
        ├── __init__.py
        └── gitea_backend.py          # GiteaBackend REST client
```

---

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests (if present)
pytest tests/

# Lint
ruff check cli_anything/
mypy cli_anything/
```
