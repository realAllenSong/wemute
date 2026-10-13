"""Other apps and system features Wemute works with."""

from __future__ import annotations

import os
import plistlib
from functools import lru_cache
from pathlib import Path

THUNDERTALK_APP = Path("/Applications/ThunderTalk.app")


def detect_app(bundle: Path) -> dict[str, object]:
    """``{"installed", "version", "path"}`` for an app bundle."""
    info_path = bundle / "Contents" / "Info.plist"
    if not info_path.is_file():
        return {"installed": False, "version": "", "path": str(bundle)}
    try:
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)
    except (OSError, ValueError, plistlib.InvalidFileException):
        info = {}
    version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")
    return {"installed": True, "version": version, "path": str(bundle)}


# ── ThunderTalk: subtitles and read-aloud through its headless CLI ────────

# ThunderTalk ≥ the build that ships `--cli` sets this Info.plist key.
CLI_PLIST_KEY = "ThunderTalkCLIVersion"


def thundertalk_app() -> Path:
    """The ThunderTalk bundle to use; ``WEMUTE_THUNDERTALK_APP`` overrides it."""
    override = os.environ.get("WEMUTE_THUNDERTALK_APP")
    if override:
        return Path(override).expanduser()
    for candidate in (THUNDERTALK_APP, Path.home() / "Applications" / "ThunderTalk.app"):
        if candidate.is_dir():
            return candidate
    return THUNDERTALK_APP


def thundertalk_binary(bundle: Path | None = None) -> Path:
    return (bundle or thundertalk_app()) / "Contents" / "MacOS" / "ThunderTalk"


@lru_cache(maxsize=4)
def _cli_version(binary: str, stamp: tuple[int, int]) -> int:
    info_path = Path(binary).parents[1] / "Info.plist"
    try:
        with info_path.open("rb") as stream:
            declared = plistlib.load(stream).get(CLI_PLIST_KEY)
        if isinstance(declared, int) and not isinstance(declared, bool):
            return declared
    except (OSError, ValueError, plistlib.InvalidFileException):
        pass
    # Builds made before the key existed: look for the CLI module by name.
    # Never run an unknown build with --cli: an old one would open its window.
    try:
        with open(binary, "rb") as stream:
            return 1 if _contains(stream, b"thundertalk.cli") else 0
    except OSError:
        return 0


def _contains(stream, needle: bytes, chunk: int = 1 << 22) -> bool:  # noqa: ANN001
    tail = b""
    while block := stream.read(chunk):
        if needle in tail + block:
            return True
        tail = block[-len(needle):]
    return False


def thundertalk_cli_version(bundle: Path | None = None) -> int:
    """0 when ThunderTalk is missing or too old for subtitles and read-aloud."""
    binary = thundertalk_binary(bundle)
    try:
        stat = binary.stat()
    except OSError:
        return 0
    return _cli_version(str(binary), (stat.st_mtime_ns, stat.st_size))


def thundertalk_available() -> bool:
    return thundertalk_cli_version() >= 1
