"""
cli-anything-jupyterlab - A complete CLI harness for JupyterLab.

Controls JupyterLab via its REST API and nbconvert CLI.
"""
from setuptools import setup, find_packages

setup(
    name="cli-anything-jupyterlab",
    version="1.0.0",
    description="A complete CLI harness for controlling JupyterLab via REST API and nbconvert",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="CLI-Anything Project",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-jupyterlab=cli_anything.jupyterlab.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Shells",
    ],
    keywords="jupyter jupyterlab cli notebook kernel automation",
)
