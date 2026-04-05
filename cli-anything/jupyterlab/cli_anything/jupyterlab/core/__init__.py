"""
cli_anything.jupyterlab.core
============================

Core orchestration layer for the JupyterLab CLI harness.

This package exposes the shared Click context object that carries
the configured :class:`~cli_anything.jupyterlab.utils.JupyterBackend`
instance across all command groups, plus helper utilities consumed
by the CLI commands.

Objects
-------
pass_backend
    Click decorator that injects the current :class:`JupyterBackend`
    instance from the Click context into a command callback.

CliContext
    Lightweight dataclass stored on the Click context object.
"""

from __future__ import annotations

import dataclasses
import sys
from typing import Optional

import click

from cli_anything.jupyterlab.utils.jupyter_backend import JupyterBackend


@dataclasses.dataclass
class CliContext:
    """Shared state threaded through Click command groups."""

    backend: JupyterBackend
    use_json: bool = False


pass_cli_ctx = click.make_pass_decorator(CliContext, ensure=True)


def make_backend(host: str, token: str) -> JupyterBackend:
    """Instantiate and (lightly) validate a :class:`JupyterBackend`."""
    backend = JupyterBackend(base_url=host, token=token)
    return backend


def error_exit(message: str, use_json: bool = False) -> None:
    """Print an error and exit with code 1."""
    import json

    if use_json:
        click.echo(json.dumps({"error": message}), err=True)
    else:
        click.secho(f"Error: {message}", fg="red", err=True)
    sys.exit(1)


__all__ = ["CliContext", "pass_cli_ctx", "make_backend", "error_exit"]
