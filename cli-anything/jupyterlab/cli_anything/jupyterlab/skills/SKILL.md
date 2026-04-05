# CLI-Anything JupyterLab Skill

**Package**: `cli-anything-jupyterlab`
**Entry-point**: `cli-anything-jupyterlab`
**Module invocation**: `python -m cli_anything.jupyterlab`

---

## Overview

A complete command-line harness for controlling a live JupyterLab / Jupyter
Server instance via its REST API and the `nbconvert` CLI.

### Key capabilities

| Area | What it does |
|------|-------------|
| **Kernel management** | List, start, stop, interrupt, restart kernels; browse kernel specs |
| **Notebook operations** | List, create, read, delete notebooks via the Contents API |
| **Code execution** | Send code to a running kernel over the Channels WebSocket; collect all output types |
| **Notebook run** | Execute every code cell in a notebook sequentially (starts/stops its own kernel) |
| **Export** | Delegate to `jupyter nbconvert` for script / HTML / PDF / Markdown / LaTeX output |
| **Sessions** | List and inspect active notebook ↔ kernel sessions |
| **Server info** | Query server version and real-time status |
| **REPL** | Interactive multi-line Python REPL backed by a live Jupyter kernel |

---

## Quick-start

```bash
# Install
pip install -e /path/to/cli-anything/jupyterlab

# Start a Jupyter server (in another terminal)
jupyter lab --no-browser --port=8888

# Use the CLI
export JUPYTER_TOKEN="mytoken"

cli-anything-jupyterlab kernel list
cli-anything-jupyterlab kernel start python3
cli-anything-jupyterlab kernel specs

cli-anything-jupyterlab notebook list
cli-anything-jupyterlab notebook create work/analysis.ipynb
cli-anything-jupyterlab notebook run work/analysis.ipynb --timeout 120

cli-anything-jupyterlab notebook export /local/path/notebook.ipynb --format html
cli-anything-jupyterlab notebook export /local/path/notebook.ipynb --format pdf --execute

cli-anything-jupyterlab server status
cli-anything-jupyterlab server version

cli-anything-jupyterlab session list

cli-anything-jupyterlab repl --kernel python3
```

---

## Global options

| Option | Env var | Default | Description |
|--------|---------|---------|-------------|
| `--json` | – | false | Output raw JSON instead of formatted tables |
| `--host TEXT` | `JUPYTER_HOST` | `http://localhost:8888` | Jupyter server URL |
| `--token TEXT` | `JUPYTER_TOKEN` | *(empty)* | Auth token |

---

## Command reference

### `kernel`

```
kernel list                        List all running kernels
kernel start [NAME]                Start a kernel (default: python3)
kernel stop KERNEL_ID              Terminate a kernel
kernel specs                       List available kernel specifications
kernel info KERNEL_ID              Show detailed kernel metadata
kernel interrupt KERNEL_ID         Send interrupt (Ctrl-C) to a kernel
kernel restart KERNEL_ID           Restart a kernel in-place
```

### `notebook`

```
notebook list [PATH]               List notebooks at server-side PATH
notebook create PATH [--kernel]    Create a new empty notebook
notebook info PATH                 Show notebook metadata and cell counts
notebook run PATH [--kernel]       Execute all code cells sequentially
           [--timeout SECS]
notebook export LOCAL_PATH         Convert using nbconvert
           [--format script|html|pdf|markdown|rst|latex|slides]
           [--output-dir DIR]
           [--execute]
notebook delete PATH [--yes]       Delete a notebook from the server
```

### `server`

```
server status                      Show server uptime, kernels, connections
server version                     Print the Jupyter Server version string
```

### `session`

```
session list                       List active sessions
session status SESSION_ID          Show details for a session
session delete SESSION_ID [--yes]  Delete a session (stops its kernel)
```

### `repl`

```
repl [--kernel-id ID]              Attach to existing kernel
     [--kernel NAME]               Or start a new one (default: python3)
     [--timeout SECS]              Per-cell execution timeout

Special commands inside REPL:
  %kernels    list running kernels
  %restart    restart current kernel
  %exit       quit (also: exit, quit, Ctrl-D)
  \           trailing backslash continues on next line (multi-line input)
```

---

## Programmatic API

```python
from cli_anything.jupyterlab.utils.jupyter_backend import JupyterBackend

backend = JupyterBackend(
    base_url="http://localhost:8888",
    token="mytoken",
    timeout=30,
)

# Kernel lifecycle
kernels      = backend.list_kernels()
kernel       = backend.start_kernel(name="python3")
kernel_id    = kernel["id"]
specs        = backend.list_kernel_specs()

# Execute code
result = backend.execute_cell(kernel_id, "1 + 1")
print(result["text"])          # "2"
print(result["status"])        # "ok"

# Run a full notebook
results = backend.run_notebook("work/analysis.ipynb")

# Export
proc = backend.export_notebook("/local/analysis.ipynb", fmt="html")

# Notebooks (Contents API)
notebooks = backend.list_notebooks()
nb        = backend.read_notebook("work/analysis.ipynb")
backend.create_notebook("new/notebook.ipynb", kernel_name="python3")

# Sessions
sessions = backend.list_sessions()

# Cleanup
backend.stop_kernel(kernel_id)
```

---

## Architecture

```
cli-anything-jupyterlab/
├── setup.py                            Package metadata & entry-point
└── cli_anything/jupyterlab/
    ├── __init__.py                     Package version
    ├── __main__.py                     `python -m cli_anything.jupyterlab`
    ├── jupyterlab_cli.py               Full Click CLI (all command groups)
    ├── core/
    │   └── __init__.py                 CliContext dataclass, shared helpers
    ├── utils/
    │   ├── __init__.py
    │   └── jupyter_backend.py          REST API wrapper (JupyterBackend)
    └── skills/
        └── SKILL.md                    This file
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `click>=8.0` | CLI framework, argument/option parsing, command groups |
| `prompt-toolkit>=3.0` | REPL history, syntax highlighting, multi-line input |
| `requests>=2.28` | HTTP client for the Jupyter REST API |
| `websocket-client` *(optional)* | WebSocket execution channel; install for `execute_cell` / `repl` |
| `nbconvert` *(optional)* | Required only for `notebook export` |
| `pygments` *(optional)* | REPL syntax highlighting |

---

## Notes & limitations

- **WebSocket execution** requires `pip install websocket-client`.  Without it,
  `execute_cell`, `notebook run`, and `repl` will raise a clear error.
- **PDF export** requires a working LaTeX installation (`texlive` / MacTeX).
- The `export` command operates on **local filesystem paths**, while
  `notebook list/create/read/run` use **server-side paths** relative to the
  Jupyter root directory.
- Token auth is the only supported authentication method.  For servers using
  password auth, pass an empty token and ensure the server is configured to
  accept unauthenticated local connections.
- JupyterLab 3.x and Jupyter Server 1.x / 2.x are supported.
  Legacy `notebook` (v6) servers expose the same API at the same endpoints.
