from setuptools import setup, find_packages

setup(
    name="cli-anything-gitea",
    version="1.0.0",
    description="CLI-Anything harness for Gitea self-hosted Git service",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
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
            "cli-anything-gitea=cli_anything.gitea.gitea_cli:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Software Development :: Version Control :: Git",
    ],
)
