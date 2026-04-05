"""
GiteaBackend
~~~~~~~~~~~~

Thin, typed wrapper around the Gitea REST API v1.
All public methods raise GiteaAPIError on non-2xx responses.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import requests
from requests import Response, Session


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GiteaAPIError(Exception):
    """Raised when the Gitea API returns an unexpected status code."""

    def __init__(self, status_code: int, message: str, url: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"HTTP {status_code}: {message} [{url}]")


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class GiteaBackend:
    """
    REST API client for a self-hosted Gitea instance.

    Parameters
    ----------
    base_url:
        Root URL of the Gitea instance, e.g. ``http://localhost:3000``.
        A trailing slash is stripped automatically.
    token:
        Personal access token.  Passed as ``Authorization: token <TOKEN>``.
    timeout:
        Per-request timeout in seconds (default 15).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        token: str = "",
        timeout: int = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

        self._session: Session = requests.Session()
        if token:
            self._session.headers.update({"Authorization": f"token {token}"})
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Build a full API URL from a path fragment."""
        return f"{self.base_url}/api/v1/{path.lstrip('/')}"

    def _raise_for_status(self, resp: Response) -> None:
        if resp.ok:
            return
        try:
            detail = resp.json().get("message", resp.text)
        except Exception:
            detail = resp.text or resp.reason
        raise GiteaAPIError(resp.status_code, detail, resp.url)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = self._session.get(self._url(path), params=params, timeout=self.timeout)
        self._raise_for_status(resp)
        return resp.json() if resp.content else {}

    def _post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        resp = self._session.post(
            self._url(path),
            data=json.dumps(payload or {}),
            timeout=self.timeout,
        )
        self._raise_for_status(resp)
        return resp.json() if resp.content else {}

    def _patch(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        resp = self._session.patch(
            self._url(path),
            data=json.dumps(payload or {}),
            timeout=self.timeout,
        )
        self._raise_for_status(resp)
        return resp.json() if resp.content else {}

    def _delete(self, path: str) -> None:
        resp = self._session.delete(self._url(path), timeout=self.timeout)
        self._raise_for_status(resp)

    # ------------------------------------------------------------------
    # Server / meta
    # ------------------------------------------------------------------

    def get_version(self) -> dict[str, Any]:
        """Return the Gitea server version info."""
        return self._get("version")

    def get_server_status(self) -> dict[str, Any]:
        """Return basic server reachability info (uses /version as a probe)."""
        data = self._get("version")
        return {"reachable": True, "version": data.get("version", "unknown")}

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    def get_user(self) -> dict[str, Any]:
        """Return the authenticated user's profile."""
        return self._get("user")

    def get_user_by_name(self, username: str) -> dict[str, Any]:
        """Return a user's public profile."""
        return self._get(f"users/{username}")

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    def list_repos(self, owner: str) -> list[dict[str, Any]]:
        """List all repositories owned by *owner* (user or org)."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._get(
                f"repos/search",
                params={"owner": owner, "limit": 50, "page": page},
            )
            items = batch.get("data", [])
            results.extend(items)
            if len(items) < 50:
                break
            page += 1
        return results

    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = False,
        default_branch: str = "main",
    ) -> dict[str, Any]:
        """Create a new repository under the authenticated user."""
        return self._post(
            "user/repos",
            {
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
                "default_branch": default_branch,
            },
        )

    def delete_repo(self, owner: str, name: str) -> None:
        """Permanently delete a repository. Use with caution."""
        self._delete(f"repos/{owner}/{name}")

    def get_repo(self, owner: str, name: str) -> dict[str, Any]:
        """Return repository metadata."""
        return self._get(f"repos/{owner}/{name}")

    def fork_repo(
        self,
        owner: str,
        name: str,
        organization: str = "",
    ) -> dict[str, Any]:
        """Fork *owner/name* into the authenticated user (or *organization*)."""
        payload: dict[str, Any] = {}
        if organization:
            payload["organization"] = organization
        return self._post(f"repos/{owner}/{name}/forks", payload)

    def search_repos(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Full-text search across all visible repositories."""
        data = self._get("repos/search", params={"q": query, "limit": limit})
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List issues for *owner/repo*.

        Parameters
        ----------
        state:
            ``"open"``, ``"closed"``, or ``"all"``.
        """
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._get(
                f"repos/{owner}/{repo}/issues",
                params={"type": "issues", "state": state, "limit": limit, "page": page},
            )
            results.extend(batch)
            if len(batch) < limit:
                break
            page += 1
        return results

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        assignees: list[str] | None = None,
        labels: list[int] | None = None,
    ) -> dict[str, Any]:
        """Open a new issue in *owner/repo*."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if assignees:
            payload["assignees"] = assignees
        if labels:
            payload["labels"] = labels
        return self._post(f"repos/{owner}/{repo}/issues", payload)

    def close_issue(self, owner: str, repo: str, issue_id: int) -> dict[str, Any]:
        """Close an existing issue by its number."""
        return self._patch(
            f"repos/{owner}/{repo}/issues/{issue_id}",
            {"state": "closed"},
        )

    def get_issue(self, owner: str, repo: str, issue_id: int) -> dict[str, Any]:
        """Fetch a single issue by its number."""
        return self._get(f"repos/{owner}/{repo}/issues/{issue_id}")

    # ------------------------------------------------------------------
    # Branches
    # ------------------------------------------------------------------

    def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List all branches in *owner/repo*."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._get(
                f"repos/{owner}/{repo}/branches",
                params={"limit": 50, "page": page},
            )
            results.extend(batch)
            if len(batch) < 50:
                break
            page += 1
        return results

    # ------------------------------------------------------------------
    # Files / content
    # ------------------------------------------------------------------

    def get_file(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str = "",
    ) -> dict[str, Any]:
        """
        Retrieve a file's metadata and decoded content.

        The returned dict has an extra ``decoded_content`` key with the
        plain-text content (base64-decoded from the API's ``content`` field).
        """
        params: dict[str, str] = {}
        if branch:
            params["ref"] = branch
        data = self._get(f"repos/{owner}/{repo}/contents/{path.lstrip('/')}", params or None)
        # Decode base64 content when present
        raw = data.get("content", "")
        if raw:
            try:
                data["decoded_content"] = base64.b64decode(raw).decode("utf-8", errors="replace")
            except Exception:
                data["decoded_content"] = raw
        else:
            data["decoded_content"] = ""
        return data

    def list_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: str = "",
    ) -> list[dict[str, Any]]:
        """List files and directories at *path* inside *owner/repo*."""
        params: dict[str, str] = {}
        if branch:
            params["ref"] = branch
        data = self._get(
            f"repos/{owner}/{repo}/contents/{path.lstrip('/')}",
            params or None,
        )
        # The endpoint returns a list for directories, a dict for files
        if isinstance(data, list):
            return data
        return [data]

    # ------------------------------------------------------------------
    # Organisations
    # ------------------------------------------------------------------

    def list_orgs(self) -> list[dict[str, Any]]:
        """List all organisations the authenticated user belongs to."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._get("user/orgs", params={"limit": 50, "page": page})
            results.extend(batch)
            if len(batch) < 50:
                break
            page += 1
        return results
