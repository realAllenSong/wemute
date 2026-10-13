"""A "Wemute 转换" shortcut for the Shortcuts app.

The shortcut takes files (from Finder, the share sheet or another shortcut),
runs ``Wemute --cli convert --plain`` on them and outputs the paths of the
converted files, so it chains into larger automations. Shortcuts only imports
signed files, so it is signed with ``shortcuts sign`` and opened for the user
to add.
"""

from __future__ import annotations

import plistlib
import shlex
import subprocess
from pathlib import Path

SHORTCUTS_CLI = Path("/usr/bin/shortcuts")
TITLES = {"zh": "Wemute 转换", "en": "Convert with Wemute"}


def shortcut_plist(command: list[str]) -> dict:
    script = f'{shlex.join(command)} --cli convert --notify --plain "$@" 2>/dev/null'
    return {
        "WFWorkflowClientVersion": "2605.0.5",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        # Blue tile with the arrows glyph.
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 463140863, "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": ["ActionExtension", "QuickActions"],
        "WFQuickActionSurfaces": ["Finder"],
        "WFWorkflowInputContentItemClasses": ["WFGenericFileContentItem"],
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.runshellscript",
                "WFWorkflowActionParameters": {
                    "Script": script,
                    "Shell": "/bin/zsh",
                    "InputMode": "as arguments",
                    "Input": {
                        "Value": {"Type": "ExtensionInput"},
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            }
        ],
    }


def build_signed(command: list[str], folder: Path, language: str) -> Path:
    """Write and sign the shortcut; returns the signed file to open."""
    folder.mkdir(parents=True, exist_ok=True)
    title = TITLES.get(language, TITLES["en"])
    unsigned = folder / "unsigned.shortcut"
    signed = folder / f"{title}.shortcut"
    unsigned.write_bytes(plistlib.dumps(shortcut_plist(command), fmt=plistlib.FMT_BINARY))
    signed.unlink(missing_ok=True)
    result = subprocess.run(
        [str(SHORTCUTS_CLI), "sign", "--mode", "anyone", "--input", str(unsigned), "--output", str(signed)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    unsigned.unlink(missing_ok=True)
    if not signed.is_file() or signed.stat().st_size == 0:
        raise RuntimeError((result.stderr or result.stdout or "shortcuts sign failed").strip().splitlines()[-1])
    return signed


def available() -> bool:
    return SHORTCUTS_CLI.exists()
