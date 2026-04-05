"""
cli_anything.jupyterlab.__main__
=================================

Allows the package to be invoked directly as a module::

    python -m cli_anything.jupyterlab [OPTIONS] COMMAND [ARGS]...

This is equivalent to running the ``cli-anything-jupyterlab`` entry-point
installed by setup.py.
"""

from cli_anything.jupyterlab.jupyterlab_cli import main

if __name__ == "__main__":
    main()
