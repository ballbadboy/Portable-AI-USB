"""
cli_anything.jupyterlab
=======================

CLI-Anything harness for JupyterLab.

Provides programmatic and command-line access to:
  - Kernel lifecycle management (list, start, stop, inspect specs)
  - Notebook operations (list, create, read, run, export)
  - Session management
  - Server status and version information
  - Interactive REPL against a live kernel

Typical usage::

    from cli_anything.jupyterlab.utils.jupyter_backend import JupyterBackend

    backend = JupyterBackend(base_url="http://localhost:8888", token="mytoken")
    kernels = backend.list_kernels()
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
