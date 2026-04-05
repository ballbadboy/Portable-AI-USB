"""Joplin REST API wrapper — the single module that makes network requests.

Joplin exposes a local HTTP API via the Web Clipper service (default: http://localhost:41184).
All requests require an API token that can be retrieved from Joplin's options under
Tools → Options → Web Clipper.

API reference: https://joplinapp.org/help/api/references/rest_api/
"""

import requests
from typing import Any

# Default Joplin Web Clipper API URL
DEFAULT_BASE_URL = "http://localhost:41184"


class JoplinBackend:
    """Thin wrapper around the Joplin REST API.

    All methods raise RuntimeError on HTTP or connection errors so that
    callers can handle them uniformly.

    Args:
        base_url: Joplin API base URL (default: http://localhost:41184).
        token: Joplin API token. If None, get_token() must be called first.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Internal helpers ─────────────────────────────────────────────────

    def _params(self, extra: dict | None = None) -> dict:
        """Build query params dict, always including the token."""
        p: dict = {"token": self.token or ""}
        if extra:
            p.update(extra)
        return p

    def _get(self, endpoint: str, params: dict | None = None, timeout: int = 15) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self._session.get(url, params=self._params(params), timeout=timeout)
            resp.raise_for_status()
            if not resp.content:
                return {"status": "ok"}
            return resp.json()
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot connect to Joplin at {self.base_url}. "
                "Is Joplin running with Web Clipper enabled?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"Joplin API error {resp.status_code} on GET {endpoint}: {resp.text}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Request timed out: GET {endpoint}") from exc

    def _post(self, endpoint: str, data: dict | None = None, timeout: int = 15) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self._session.post(
                url, json=data or {}, params=self._params(), timeout=timeout
            )
            resp.raise_for_status()
            if not resp.content:
                return {"status": "ok"}
            return resp.json()
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot connect to Joplin at {self.base_url}. "
                "Is Joplin running with Web Clipper enabled?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"Joplin API error {resp.status_code} on POST {endpoint}: {resp.text}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Request timed out: POST {endpoint}") from exc

    def _put(self, endpoint: str, data: dict | None = None, timeout: int = 15) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self._session.put(
                url, json=data or {}, params=self._params(), timeout=timeout
            )
            resp.raise_for_status()
            if not resp.content:
                return {"status": "ok"}
            return resp.json()
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot connect to Joplin at {self.base_url}. "
                "Is Joplin running with Web Clipper enabled?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"Joplin API error {resp.status_code} on PUT {endpoint}: {resp.text}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Request timed out: PUT {endpoint}") from exc

    def _delete(self, endpoint: str, timeout: int = 15) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self._session.delete(url, params=self._params(), timeout=timeout)
            resp.raise_for_status()
            if not resp.content:
                return {"status": "ok"}
            return resp.json()
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot connect to Joplin at {self.base_url}. "
                "Is Joplin running with Web Clipper enabled?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"Joplin API error {resp.status_code} on DELETE {endpoint}: {resp.text}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Request timed out: DELETE {endpoint}") from exc

    # ── Token ────────────────────────────────────────────────────────────

    def get_token(self) -> str:
        """Return the currently configured API token.

        Raises:
            RuntimeError: If no token is set.
        """
        if not self.token:
            raise RuntimeError(
                "No Joplin API token set. "
                "Get your token from Joplin → Tools → Options → Web Clipper, "
                "then pass it via --token or set JOPLIN_TOKEN environment variable."
            )
        return self.token

    # ── Notes ────────────────────────────────────────────────────────────

    def list_notes(self, limit: int = 100, page: int = 1,
                   fields: str = "id,title,parent_id,updated_time,created_time") -> dict:
        """List notes with pagination.

        Args:
            limit: Maximum number of notes to return (1-100).
            page: Page number for pagination (1-based).
            fields: Comma-separated list of fields to include in the response.

        Returns:
            Dict with 'items' list and 'has_more' bool.
        """
        return self._get("/notes", params={
            "limit": limit,
            "page": page,
            "fields": fields,
            "order_by": "updated_time",
            "order_dir": "DESC",
        })

    def get_note(self, note_id: str,
                 fields: str = "id,title,body,parent_id,updated_time,created_time") -> dict:
        """Retrieve a single note by ID.

        Args:
            note_id: The note's unique identifier.
            fields: Comma-separated list of fields to return.

        Returns:
            Note dict with requested fields.
        """
        return self._get(f"/notes/{note_id}", params={"fields": fields})

    def create_note(self, title: str, body: str = "",
                    notebook_id: str | None = None) -> dict:
        """Create a new note.

        Args:
            title: Note title.
            body: Note body in Markdown.
            notebook_id: Parent notebook ID. Defaults to the default notebook if None.

        Returns:
            Created note dict with at least 'id' and 'title'.
        """
        payload: dict = {"title": title, "body": body}
        if notebook_id:
            payload["parent_id"] = notebook_id
        return self._post("/notes", data=payload)

    def update_note(self, note_id: str, title: str | None = None,
                    body: str | None = None) -> dict:
        """Update an existing note's title and/or body.

        Args:
            note_id: The note's unique identifier.
            title: New title, or None to leave unchanged.
            body: New body content, or None to leave unchanged.

        Returns:
            Updated note dict.
        """
        payload: dict = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if not payload:
            raise ValueError("At least one of title or body must be provided.")
        return self._put(f"/notes/{note_id}", data=payload)

    def delete_note(self, note_id: str) -> dict:
        """Permanently delete a note.

        Args:
            note_id: The note's unique identifier.

        Returns:
            {'status': 'ok'} on success.
        """
        return self._delete(f"/notes/{note_id}")

    # ── Notebooks ────────────────────────────────────────────────────────

    def list_notebooks(self, limit: int = 100, page: int = 1,
                       fields: str = "id,title,parent_id,updated_time") -> dict:
        """List all notebooks (folders).

        Args:
            limit: Maximum number of notebooks to return.
            page: Page number for pagination.
            fields: Comma-separated list of fields to include.

        Returns:
            Dict with 'items' list and 'has_more' bool.
        """
        return self._get("/folders", params={
            "limit": limit,
            "page": page,
            "fields": fields,
        })

    def create_notebook(self, title: str,
                        parent_id: str | None = None) -> dict:
        """Create a new notebook (folder).

        Args:
            title: Notebook title.
            parent_id: Parent notebook ID for nested notebooks, or None for root.

        Returns:
            Created notebook dict with at least 'id' and 'title'.
        """
        payload: dict = {"title": title}
        if parent_id:
            payload["parent_id"] = parent_id
        return self._post("/folders", data=payload)

    def delete_notebook(self, notebook_id: str) -> dict:
        """Delete a notebook (folder) and all its notes.

        Args:
            notebook_id: The notebook's unique identifier.

        Returns:
            {'status': 'ok'} on success.
        """
        return self._delete(f"/folders/{notebook_id}")

    # ── Search ───────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20,
               fields: str = "id,title,parent_id,updated_time") -> dict:
        """Full-text search across notes.

        Args:
            query: Search query string. Supports Joplin search syntax.
            limit: Maximum number of results to return.
            fields: Comma-separated list of fields to include in results.

        Returns:
            Dict with 'items' list of matching notes and 'has_more' bool.
        """
        return self._get("/search", params={
            "query": query,
            "limit": limit,
            "fields": fields,
        })

    # ── Tags ─────────────────────────────────────────────────────────────

    def list_tags(self, limit: int = 100, page: int = 1) -> dict:
        """List all tags.

        Args:
            limit: Maximum number of tags to return.
            page: Page number for pagination.

        Returns:
            Dict with 'items' list and 'has_more' bool.
        """
        return self._get("/tags", params={
            "limit": limit,
            "page": page,
            "fields": "id,title",
        })

    def add_tag(self, note_id: str, tag_id: str) -> dict:
        """Apply an existing tag to a note.

        Args:
            note_id: The note's unique identifier.
            tag_id: The tag's unique identifier.

        Returns:
            {'status': 'ok'} on success.
        """
        return self._post(f"/tags/{tag_id}/notes", data={"id": note_id})

    # ── Connectivity check ───────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if the Joplin API is reachable (ignoring auth)."""
        try:
            resp = requests.get(
                f"{self.base_url}/ping", timeout=5
            )
            return resp.status_code == 200
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return False
