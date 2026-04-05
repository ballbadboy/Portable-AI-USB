---
name: >-
  cli-anything-joplin
description: >-
  Command-line interface for Joplin - Note-taking app management via the Joplin Web Clipper REST API. Designed for AI agents and power users who need to create, read, update, delete, and search notes without opening the Joplin GUI.
---

# cli-anything-joplin

Note management for Joplin via the Web Clipper REST API (http://localhost:41184).
Designed for AI agents and power users who need full note-taking control from the terminal.

## Installation

```bash
pip install cli-anything-joplin
```

**Prerequisites:**
- Python 3.10+
- Joplin desktop app running with Web Clipper enabled
  (Tools → Options → Web Clipper → Enable Web Clipper service)
- Your API token from the same Web Clipper settings page


## Authentication

All commands require a Joplin API token. Provide it with:

```bash
# Option 1: --token flag (per command)
cli-anything-joplin --token <TOKEN> note list

# Option 2: environment variable (recommended for scripts/agents)
export JOPLIN_TOKEN=<TOKEN>
cli-anything-joplin note list
```


## Usage

### Basic Commands

```bash
# Show help
cli-anything-joplin --help

# Start interactive REPL mode
cli-anything-joplin --token <TOKEN>

# List notes (most recently updated first)
cli-anything-joplin --token <TOKEN> note list

# Output as JSON (for agent consumption)
cli-anything-joplin --token <TOKEN> --json note list
```

### REPL Mode

When invoked without a subcommand, the CLI enters an interactive REPL session
with command history, auto-suggest, and tab completion:

```bash
export JOPLIN_TOKEN=<TOKEN>
cli-anything-joplin
# joplin ❯ note list
# joplin ❯ note search "project"
# joplin ❯ quit
```


## Command Groups


### note

Note management commands.

| Command | Description |
|---------|-------------|
| `list`   | List notes, most-recently-updated first |
| `get`    | Get a note's full content by ID |
| `create` | Create a new note |
| `edit`   | Update an existing note's title and/or body |
| `delete` | Permanently delete a note by ID |
| `search` | Full-text search across all notes |


### notebook

Notebook (folder) management commands.

| Command  | Description |
|----------|-------------|
| `list`   | List all notebooks |
| `create` | Create a new notebook |
| `delete` | Delete a notebook and all notes inside it |


### tag

Tag management commands.

| Command | Description |
|---------|-------------|
| `list`  | List all tags |
| `add`   | Apply an existing tag to a note |


### session

Session and connection state commands.

| Command  | Description |
|----------|-------------|
| `status` | Show current session configuration and API connectivity |


## Examples


### Working with Notes

```bash
# List the 10 most recent notes
cli-anything-joplin --token $T note list --limit 10

# Get the full content of a note (use the ID from list)
cli-anything-joplin --token $T note get <NOTE_ID>

# Create a note in the default notebook
cli-anything-joplin --token $T note create --title "Meeting Notes" --body "# Agenda\n- Item 1"

# Create a note from a file
cli-anything-joplin --token $T note create --title "Report" --body-file report.md --notebook <NOTEBOOK_ID>

# Update just the title
cli-anything-joplin --token $T note edit <NOTE_ID> --title "New Title"

# Update just the body
cli-anything-joplin --token $T note edit <NOTE_ID> --body "Updated content"

# Delete a note (prompts for confirmation)
cli-anything-joplin --token $T note delete <NOTE_ID>

# Delete without confirmation (for scripting)
cli-anything-joplin --token $T note delete <NOTE_ID> --yes
```


### Searching Notes

```bash
# Basic search
cli-anything-joplin --token $T note search "quarterly report"

# Search with more results
cli-anything-joplin --token $T note search "meeting" --limit 50

# Search and get JSON output
cli-anything-joplin --token $T --json note search "todo"
```

Joplin search supports full-text queries and field-specific search:

```bash
cli-anything-joplin --token $T note search "title:project"
cli-anything-joplin --token $T note search "body:budget AND year:2025"
```


### Working with Notebooks

```bash
# List all notebooks
cli-anything-joplin --token $T notebook list

# Create a root-level notebook
cli-anything-joplin --token $T notebook create --title "Work"

# Create a nested notebook
cli-anything-joplin --token $T notebook create --title "Q1 2025" --parent <PARENT_ID>

# Delete a notebook (and all its notes — irreversible!)
cli-anything-joplin --token $T notebook delete <NOTEBOOK_ID> --yes
```


### Working with Tags

```bash
# List all tags
cli-anything-joplin --token $T tag list

# Apply a tag to a note
cli-anything-joplin --token $T tag add <NOTE_ID> <TAG_ID>
```


### Custom Host

```bash
# Connect to a Joplin server on a different host/port
cli-anything-joplin --host http://192.168.1.50:41184 --token $T note list
```


### Check Connection

```bash
cli-anything-joplin --token $T session status
```


## Output Formats

All commands support dual output modes:

- **Human-readable** (default): Tables, aligned columns, formatted timestamps
- **Machine-readable** (`--json` flag): Structured JSON for agent/script consumption

```bash
# Human output
cli-anything-joplin --token $T note list

# JSON output for agents
cli-anything-joplin --token $T --json note list
```


## For AI Agents

When using this CLI programmatically:

1. **Always use `--json` flag** for parseable output
2. **Set `JOPLIN_TOKEN` env var** rather than passing `--token` in every command
3. **Check return codes** — 0 for success, non-zero for errors
4. **Parse stderr** for error messages on failure
5. **Verify connectivity** with `session status` before running batch operations
6. **Use `--yes` flag** on delete commands to avoid interactive confirmation prompts
7. **Paginate large results** using `--limit` and `--page` flags

### Agent workflow example

```bash
export JOPLIN_TOKEN=<TOKEN>

# Verify connected
cli-anything-joplin --json session status

# Search for a note
cli-anything-joplin --json note search "project proposal" --limit 5

# Get the full content (use the id from search results)
cli-anything-joplin --json note get <NOTE_ID>

# Create a new note with content
cli-anything-joplin --json note create --title "Agent Summary" --body "Generated by AI agent"
```


## State Management

The CLI maintains lightweight session state:

- **Current host URL**: Configurable via `--host` (or `_host` global in REPL)
- **API token**: Passed via `--token` or `JOPLIN_TOKEN` environment variable
- **JSON output mode**: Configurable via `--json` global flag


## Version

1.0.0
