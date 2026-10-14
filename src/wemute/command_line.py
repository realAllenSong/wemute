"""The `wemute` shell command: a two-line script that runs ``Wemute --cli``.

Installed from 设置 · 集成 so scripts and agents can call
``wemute extract report.pdf`` instead of the path inside the app bundle. It
goes into the first writable folder on PATH from a short list (Homebrew's bin
on Apple Silicon is writable by the user), else ``~/.local/bin``.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

MARKER = "# Installed by Wemute"
CANDIDATES = (Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path.home() / ".local" / "bin")


def script(command: list[str]) -> str:
    return f'#!/bin/sh\n{MARKER} (Settings › Integrations). Runs Wemute without a window.\nexec {shlex.join(command)} --cli "$@"\n'


def _on_path(folder: Path) -> bool:
    return str(folder) in os.environ.get("PATH", "").split(os.pathsep)


def target_folder() -> Path:
    for folder in CANDIDATES:
        if folder.is_dir() and os.access(folder, os.W_OK) and (_on_path(folder) or folder == CANDIDATES[0]):
            return folder
    return CANDIDATES[-1]


def installed_path() -> Path | None:
    for folder in CANDIDATES:
        path = folder / "wemute"
        try:
            if path.is_file() and MARKER in path.read_text(encoding="utf-8", errors="replace")[:400]:
                return path
        except OSError:
            continue
    return None


def install(command: list[str], folder: Path | None = None) -> Path:
    folder = folder or target_folder()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "wemute"
    if path.exists() and MARKER not in path.read_text(encoding="utf-8", errors="replace")[:400]:
        raise FileExistsError(f"{path} already exists and was not made by Wemute")
    path.write_text(script(command), encoding="utf-8")
    path.chmod(0o755)
    return path


def remove() -> bool:
    path = installed_path()
    if path is None:
        return False
    path.unlink()
    return True
