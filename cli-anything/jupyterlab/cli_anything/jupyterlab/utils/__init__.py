"""
cli_anything.jupyterlab.utils
==============================

Utility modules for the JupyterLab CLI harness.

Modules
-------
jupyter_backend
    Low-level REST API wrapper around the Jupyter Server HTTP API.
    Provides :class:`JupyterBackend` for kernels, notebooks, sessions,
    and nbconvert-based exports.
"""

from cli_anything.jupyterlab.utils.jupyter_backend import JupyterBackend

__all__ = ["JupyterBackend"]
