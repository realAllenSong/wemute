"""Other apps and system features Wemute works with."""

from __future__ import annotations

import plistlib
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
