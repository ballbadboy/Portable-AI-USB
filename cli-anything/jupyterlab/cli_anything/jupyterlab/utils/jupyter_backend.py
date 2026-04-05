"""
cli_anything.jupyterlab.utils.jupyter_backend
==============================================

Low-level wrapper around the Jupyter Server REST API (v1).

Supports:
  - Kernel lifecycle  : list, start, stop, inspect kernel specs
  - Notebook CRUD     : list, create, read notebooks on the server
  - Code execution    : send code to a live kernel over the Channels WebSocket
                        (graceful fallback when websocket-client is absent)
  - Export            : delegate to ``jupyter nbconvert`` subprocess
  - Sessions          : list, inspect active sessions

The Jupyter Server REST API reference:
  https://jupyter-server.readthedocs.io/en/latest/developers/rest-api.html

All public methods raise :class:`JupyterBackendError` on failure so that
callers can catch a single predictable exception type.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from requests import Response, Session


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JupyterBackendError(Exception):
    """Raised for any Jupyter Server communication or configuration error."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    def __str__(self) -> str:  # pragma: no cover
        base = super().__str__()
        if self.status_code is not None:
            return f"[HTTP {self.status_code}] {base}"
        return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_websocket_client() -> Any:
    """Import websocket-client lazily; raise a clear error when absent."""
    try:
        import websocket  # type: ignore[import]

        return websocket
    except ImportError as exc:
        raise JupyterBackendError(
            "Package 'websocket-client' is required for kernel execution. "
            "Install it with: pip install websocket-client"
        ) from exc


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class JupyterBackend:
    """Thin, stateless wrapper around the Jupyter Server REST API.

    Parameters
    ----------
    base_url:
        Root URL of the Jupyter server, e.g. ``http://localhost:8888``.
        A trailing slash is normalised automatically.
    token:
        Server authentication token.  Pass an empty string when the server
        runs without authentication (not recommended in production).
    timeout:
        Default HTTP timeout in seconds for all requests.

    Examples
    --------
    >>> backend = JupyterBackend("http://localhost:8888", token="secret")
    >>> backend.list_kernels()
    [{'id': '...', 'name': 'python3', ...}]
    """

    _API_PREFIX = "/api"

    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        token: str = "",
        timeout: int = 30,
    ) -> None:
        # Normalise base URL: strip trailing slash, ensure scheme present.
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = "http://" + base_url
        self.base_url: str = base_url.rstrip("/")
        self.token: str = token
        self.timeout: int = timeout

        self._session: Session = requests.Session()
        if token:
            self._session.headers.update({"Authorization": f"token {token}"})
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _url(self, *parts: str) -> str:
        """Build an absolute API URL from path parts."""
        path = "/".join(p.strip("/") for p in parts if p)
        return f"{self.base_url}{self._API_PREFIX}/{path}"

    def _get(self, *parts: str, params: Optional[Dict] = None) -> Any:
        url = self._url(*parts)
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise JupyterBackendError(
                f"Cannot connect to Jupyter server at {self.base_url}. "
                "Is the server running?"
            ) from exc
        except requests.Timeout as exc:
            raise JupyterBackendError(
                f"Request to {url} timed out after {self.timeout}s"
            ) from exc
        self._raise_for_status(resp)
        return resp.json()

    def _post(self, *parts: str, data: Any = None) -> Any:
        url = self._url(*parts)
        try:
            resp = self._session.post(
                url,
                data=json.dumps(data) if data is not None else None,
                timeout=self.timeout,
            )
        except requests.ConnectionError as exc:
            raise JupyterBackendError(
                f"Cannot connect to Jupyter server at {self.base_url}."
            ) from exc
        self._raise_for_status(resp)
        try:
            return resp.json()
        except ValueError:
            return {}

    def _delete(self, *parts: str) -> None:
        url = self._url(*parts)
        try:
            resp = self._session.delete(url, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise JupyterBackendError(
                f"Cannot connect to Jupyter server at {self.base_url}."
            ) from exc
        self._raise_for_status(resp)

    def _put(self, *parts: str, data: Any = None) -> Any:
        url = self._url(*parts)
        try:
            resp = self._session.put(
                url,
                data=json.dumps(data) if data is not None else None,
                timeout=self.timeout,
            )
        except requests.ConnectionError as exc:
            raise JupyterBackendError(
                f"Cannot connect to Jupyter server at {self.base_url}."
            ) from exc
        self._raise_for_status(resp)
        try:
            return resp.json()
        except ValueError:
            return {}

    @staticmethod
    def _raise_for_status(resp: Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message", resp.text)
            except ValueError:
                detail = resp.text or resp.reason
            raise JupyterBackendError(detail, status_code=resp.status_code)

    # ------------------------------------------------------------------
    # Server info
    # ------------------------------------------------------------------

    def server_info(self) -> Dict[str, Any]:
        """Return server version and configuration details.

        Returns
        -------
        dict
            Keys include ``version``, ``sys_version``, ``python_version``,
            ``started``, ``last_activity``, ``connections``, ``kernels``.
        """
        return self._get("status")

    def server_version(self) -> str:
        """Return just the Jupyter Server version string."""
        info = self.server_info()
        return info.get("version", "unknown")

    # ------------------------------------------------------------------
    # Kernels
    # ------------------------------------------------------------------

    def list_kernels(self) -> List[Dict[str, Any]]:
        """List all currently running kernels.

        Returns
        -------
        list of dict
            Each dict has keys: ``id``, ``name``, ``last_activity``,
            ``execution_state``, ``connections``.
        """
        return self._get("kernels")

    def start_kernel(self, name: str = "python3") -> Dict[str, Any]:
        """Start a new kernel with the given kernel spec name.

        Parameters
        ----------
        name:
            Kernel spec name (e.g. ``"python3"``, ``"ir"``, ``"julia-1.9"``).

        Returns
        -------
        dict
            Newly created kernel object including ``id``.
        """
        return self._post("kernels", data={"name": name})

    def stop_kernel(self, kernel_id: str) -> None:
        """Terminate a running kernel by its ID.

        Parameters
        ----------
        kernel_id:
            UUID of the kernel to stop.
        """
        self._delete("kernels", kernel_id)

    def list_kernel_specs(self) -> Dict[str, Any]:
        """Return all available kernel specifications.

        Returns
        -------
        dict
            ``{"default": "python3", "kernelspecs": {"python3": {...}, ...}}``.
        """
        return self._get("kernelspecs")

    def get_kernel(self, kernel_id: str) -> Dict[str, Any]:
        """Fetch a single kernel's metadata.

        Parameters
        ----------
        kernel_id:
            UUID of the kernel.
        """
        return self._get("kernels", kernel_id)

    def interrupt_kernel(self, kernel_id: str) -> None:
        """Send an interrupt signal to a kernel (equivalent to Ctrl-C)."""
        self._post("kernels", kernel_id, "interrupt")

    def restart_kernel(self, kernel_id: str) -> Dict[str, Any]:
        """Restart a kernel without destroying it."""
        return self._post("kernels", kernel_id, "restart")

    # ------------------------------------------------------------------
    # Notebooks / Contents API
    # ------------------------------------------------------------------

    def list_notebooks(self, path: str = "") -> List[Dict[str, Any]]:
        """List notebooks at the given server-side path.

        Parameters
        ----------
        path:
            Directory path relative to the Jupyter root, e.g. ``"projects/"``.
            Pass an empty string (default) for the root directory.

        Returns
        -------
        list of dict
            Only items whose ``type`` is ``"notebook"`` are returned.
        """
        result = self._get("contents", path, params={"type": "directory"})
        entries: List[Dict] = result.get("content", []) or []
        return [e for e in entries if e.get("type") == "notebook"]

    def list_files(self, path: str = "") -> List[Dict[str, Any]]:
        """List all content (files, notebooks, directories) at *path*."""
        result = self._get("contents", path, params={"type": "directory"})
        return result.get("content", []) or []

    def create_notebook(
        self,
        path: str,
        kernel_name: str = "python3",
    ) -> Dict[str, Any]:
        """Create a new empty notebook at the given path.

        Parameters
        ----------
        path:
            Desired path for the notebook, e.g. ``"work/analysis.ipynb"``.
        kernel_name:
            Kernel spec to embed in the notebook metadata.

        Returns
        -------
        dict
            The newly created contents model (without cell content).
        """
        nbformat_minor = 5
        notebook_content: Dict[str, Any] = {
            "nbformat": 4,
            "nbformat_minor": nbformat_minor,
            "metadata": {
                "kernelspec": {
                    "display_name": kernel_name,
                    "language": "python",
                    "name": kernel_name,
                },
                "language_info": {"name": "python"},
            },
            "cells": [],
        }
        payload: Dict[str, Any] = {
            "type": "notebook",
            "format": "json",
            "content": notebook_content,
        }
        return self._put("contents", path, data=payload)

    def read_notebook(self, path: str) -> Dict[str, Any]:
        """Read and return a notebook's full contents model.

        Parameters
        ----------
        path:
            Server-side path to the ``.ipynb`` file.

        Returns
        -------
        dict
            Full contents model including ``content`` (the notebook JSON).
        """
        return self._get("contents", path, params={"type": "notebook", "format": "json"})

    def save_notebook(self, path: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Write back a modified notebook content model.

        Parameters
        ----------
        path:
            Server-side path to the ``.ipynb`` file.
        content:
            The notebook dict (nbformat structure) to save.
        """
        payload: Dict[str, Any] = {
            "type": "notebook",
            "format": "json",
            "content": content,
        }
        return self._put("contents", path, data=payload)

    def delete_file(self, path: str) -> None:
        """Delete a file or notebook from the server."""
        self._delete("contents", path)

    # ------------------------------------------------------------------
    # Code execution via Kernel Channels (WebSocket)
    # ------------------------------------------------------------------

    def execute_cell(
        self,
        kernel_id: str,
        code: str,
        timeout: int = 60,
        silent: bool = False,
    ) -> Dict[str, Any]:
        """Execute *code* in the given kernel and collect all outputs.

        Communication follows the Jupyter messaging protocol over WebSocket.
        Requires the ``websocket-client`` package.

        Parameters
        ----------
        kernel_id:
            UUID of the running kernel.
        code:
            Python (or other language) source code to execute.
        timeout:
            Maximum seconds to wait for execution to finish.
        silent:
            When ``True`` the execution is not stored in kernel history.

        Returns
        -------
        dict
            ``{
                "status": "ok" | "error",
                "outputs": [...],          # list of output dicts
                "text": str,               # concatenated plain-text outputs
                "execution_count": int,
                "error": None | {"ename": ..., "evalue": ..., "traceback": [...]}
            }``

        Raises
        ------
        JupyterBackendError
            If websocket-client is not installed, the kernel is unreachable,
            or execution times out.
        """
        websocket = _require_websocket_client()

        # Build the WebSocket URL.
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base}/api/kernels/{kernel_id}/channels"
        if self.token:
            ws_url += f"?token={self.token}"

        msg_id = str(uuid.uuid4())
        execute_request = {
            "header": {
                "msg_id": msg_id,
                "username": "cli-anything",
                "session": str(uuid.uuid4()),
                "date": datetime.now(timezone.utc).isoformat(),
                "msg_type": "execute_request",
                "version": "5.3",
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": code,
                "silent": silent,
                "store_history": not silent,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            "buffers": [],
            "channel": "shell",
        }

        outputs: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        result: Dict[str, Any] = {
            "status": "ok",
            "outputs": outputs,
            "text": "",
            "execution_count": None,
            "error": None,
        }
        done_event = threading.Event()
        error_holder: List[Exception] = []

        def _on_message(ws: Any, raw: str) -> None:  # noqa: ANN001
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                return

            parent_id = msg.get("parent_header", {}).get("msg_id")
            if parent_id != msg_id:
                return

            msg_type: str = msg.get("msg_type", "")
            content: Dict[str, Any] = msg.get("content", {})

            if msg_type == "stream":
                text = content.get("text", "")
                text_parts.append(text)
                outputs.append({"output_type": "stream", "name": content.get("name", "stdout"), "text": text})

            elif msg_type == "execute_result":
                data = content.get("data", {})
                text_repr = data.get("text/plain", "")
                text_parts.append(text_repr + "\n")
                outputs.append(
                    {
                        "output_type": "execute_result",
                        "execution_count": content.get("execution_count"),
                        "data": data,
                        "metadata": content.get("metadata", {}),
                    }
                )
                result["execution_count"] = content.get("execution_count")

            elif msg_type == "display_data":
                data = content.get("data", {})
                text_repr = data.get("text/plain", "<display_data>")
                text_parts.append(text_repr + "\n")
                outputs.append(
                    {
                        "output_type": "display_data",
                        "data": data,
                        "metadata": content.get("metadata", {}),
                    }
                )

            elif msg_type == "error":
                result["status"] = "error"
                traceback = content.get("traceback", [])
                # Strip ANSI escape codes for clean text output.
                import re
                ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
                clean_tb = [ansi_escape.sub("", line) for line in traceback]
                result["error"] = {
                    "ename": content.get("ename", ""),
                    "evalue": content.get("evalue", ""),
                    "traceback": clean_tb,
                }
                text_parts.append(
                    f"{content.get('ename')}: {content.get('evalue')}\n"
                    + "\n".join(clean_tb)
                )

            elif msg_type == "execute_reply":
                result["status"] = content.get("status", "ok")
                if result["execution_count"] is None:
                    result["execution_count"] = content.get("execution_count")
                done_event.set()

        def _on_error(ws: Any, exc: Exception) -> None:  # noqa: ANN001
            error_holder.append(exc)
            done_event.set()

        def _on_open(ws: Any) -> None:  # noqa: ANN001
            ws.send(json.dumps(execute_request))

        ws_app = websocket.WebSocketApp(
            ws_url,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
        )

        ws_thread = threading.Thread(target=ws_app.run_forever, daemon=True)
        ws_thread.start()

        finished = done_event.wait(timeout=timeout)
        ws_app.close()

        if error_holder:
            raise JupyterBackendError(
                f"WebSocket error during execution: {error_holder[0]}"
            ) from error_holder[0]

        if not finished:
            raise JupyterBackendError(
                f"Kernel execution timed out after {timeout}s"
            )

        result["text"] = "".join(text_parts)
        return result

    # ------------------------------------------------------------------
    # Export via nbconvert
    # ------------------------------------------------------------------

    def export_notebook(
        self,
        path: str,
        fmt: str = "script",
        output_dir: Optional[str] = None,
        execute: bool = False,
    ) -> subprocess.CompletedProcess:
        """Export a notebook using ``jupyter nbconvert``.

        Parameters
        ----------
        path:
            Local filesystem path to the ``.ipynb`` file.
        fmt:
            nbconvert export format: ``"script"``, ``"html"``, ``"pdf"``,
            ``"markdown"``, ``"rst"``, ``"latex"``, ``"slides"``, etc.
        output_dir:
            Directory to write the converted output.  Defaults to the same
            directory as the notebook.
        execute:
            When ``True`` passes ``--execute`` to nbconvert so the notebook
            is run before conversion.

        Returns
        -------
        subprocess.CompletedProcess
            Contains ``returncode``, ``stdout``, ``stderr``.

        Raises
        ------
        JupyterBackendError
            When ``jupyter nbconvert`` is not found on PATH or exits non-zero.
        """
        notebook_path = Path(path).expanduser().resolve()
        if not notebook_path.exists():
            raise JupyterBackendError(f"Notebook not found: {notebook_path}")

        cmd: List[str] = [
            sys.executable,
            "-m",
            "nbconvert",
            "--to",
            fmt,
            str(notebook_path),
        ]
        if output_dir:
            cmd += ["--output-dir", str(Path(output_dir).expanduser().resolve())]
        if execute:
            cmd.append("--execute")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise JupyterBackendError(
                "Could not find 'jupyter nbconvert'. "
                "Install it with: pip install nbconvert"
            ) from exc

        if proc.returncode != 0:
            raise JupyterBackendError(
                f"nbconvert exited with code {proc.returncode}: {proc.stderr.strip()}"
            )
        return proc

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions on the server.

        Returns
        -------
        list of dict
            Each dict includes ``id``, ``path``, ``name``, ``type``,
            and ``kernel`` (a kernel model dict).
        """
        return self._get("sessions")

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Fetch a single session by its ID."""
        return self._get("sessions", session_id)

    def delete_session(self, session_id: str) -> None:
        """Destroy a session (and its associated kernel)."""
        self._delete("sessions", session_id)

    def create_session(
        self,
        path: str,
        kernel_name: str = "python3",
        session_type: str = "notebook",
    ) -> Dict[str, Any]:
        """Create a new session for a notebook path.

        Parameters
        ----------
        path:
            Server-side notebook path (used as the session name).
        kernel_name:
            Kernel spec to start.
        session_type:
            Session type string (``"notebook"`` or ``"console"``).

        Returns
        -------
        dict
            New session model including the started ``kernel``.
        """
        payload = {
            "path": path,
            "name": Path(path).name,
            "type": session_type,
            "kernel": {"name": kernel_name},
        }
        return self._post("sessions", data=payload)

    # ------------------------------------------------------------------
    # Terminals (bonus, for completeness)
    # ------------------------------------------------------------------

    def list_terminals(self) -> List[Dict[str, Any]]:
        """List active terminal sessions on the server."""
        return self._get("terminals")

    # ------------------------------------------------------------------
    # Convenience: run all cells in a notebook sequentially
    # ------------------------------------------------------------------

    def run_notebook(
        self,
        path: str,
        kernel_name: str = "python3",
        cell_timeout: int = 120,
    ) -> List[Dict[str, Any]]:
        """Execute every code cell in a notebook in order.

        A fresh kernel is started, all code cells run sequentially, and
        the kernel is stopped afterwards (even on error).

        Parameters
        ----------
        path:
            Server-side path to the ``.ipynb`` notebook.
        kernel_name:
            Kernel spec to use.
        cell_timeout:
            Seconds to wait for each individual cell to finish.

        Returns
        -------
        list of dict
            One result dict per executed code cell (see :meth:`execute_cell`).
        """
        notebook = self.read_notebook(path)
        cells = notebook.get("content", {}).get("cells", [])

        kernel = self.start_kernel(name=kernel_name)
        kernel_id: str = kernel["id"]
        results: List[Dict[str, Any]] = []

        try:
            for cell in cells:
                if cell.get("cell_type") != "code":
                    continue
                source = "".join(cell.get("source", []))
                if not source.strip():
                    continue
                result = self.execute_cell(kernel_id, source, timeout=cell_timeout)
                results.append(result)
                if result["status"] == "error":
                    # Stop on first error to match default notebook behaviour.
                    break
        finally:
            try:
                self.stop_kernel(kernel_id)
            except JupyterBackendError:
                pass  # Best-effort cleanup.

        return results
