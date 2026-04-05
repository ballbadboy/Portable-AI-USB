from setuptools import setup, find_packages

setup(
    name="cli-anything-meeting",
    version="1.0.0",
    description="Meeting Assistant CLI - record, transcribe, translate, and summarize meetings using Gemma 4 via Ollama",
    author="CLI-Anything",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "audio": [
            "sounddevice",
            "numpy",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-meeting=cli_anything.meeting.meeting_cli:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Office/Business",
    ],
)
