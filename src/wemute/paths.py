from __future__ import annotations

import os
import shutil
from pathlib import Path

from platformdirs import user_cache_path, user_data_path


APP_NAME = "Wemute"
PACKAGE_ROOT = Path(__file__).resolve().parent
QML_ROOT = PACKAGE_ROOT / "qml"
ASSET_ROOT = PACKAGE_ROOT / "assets"
DATA_ROOT = (
    Path(os.environ["WEMUTE_DATA_DIR"]).expanduser()
    if os.environ.get("WEMUTE_DATA_DIR")
    else user_data_path(APP_NAME, appauthor=False, ensure_exists=True)
)
CACHE_ROOT = (
    Path(os.environ["WEMUTE_CACHE_DIR"]).expanduser()
    if os.environ.get("WEMUTE_CACHE_DIR")
    else user_cache_path(APP_NAME, appauthor=False, ensure_exists=True)
)
DATA_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
THUMBNAIL_ROOT = CACHE_ROOT / "thumbnails"
THUMBNAIL_ROOT.mkdir(parents=True, exist_ok=True)


def _candidate_engine_paths(name: str) -> list[Path]:
    env_name = f"WEMUTE_{name.upper()}"
    # Packaged runtimes are resolved before system PATH.
    candidates: list[Path] = [
        PACKAGE_ROOT / "runtime" / "bin" / name,
        PACKAGE_ROOT.parent.parent / "runtime" / "bin" / name,
    ]
    if configured := os.environ.get(env_name):
        candidates.append(Path(configured).expanduser())

    # Finder-launched macOS apps do not inherit an interactive shell's PATH.
    # Probe the two conventional package-manager locations explicitly.
    candidates.extend(
        [
            Path("/opt/homebrew/bin") / name,
            Path("/usr/local/bin") / name,
        ]
    )
    if system_path := shutil.which(name):
        candidates.append(Path(system_path))
    return candidates


def resolve_engine(name: str) -> Path | None:
    for candidate in _candidate_engine_paths(name):
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate.resolve()
        except OSError:
            continue
    return None
