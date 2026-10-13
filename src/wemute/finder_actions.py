"""Finder Quick Actions (right-click › 快速操作) that run Wemute.

Each one is an Automator Quick Action in ``~/Library/Services``: a single
"Run Shell Script" step that hands the selected files to ``Wemute --cli`` (no
window, a notification when done) or opens them in the Wemute window.
"""

from __future__ import annotations

import plistlib
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

SERVICES = Path.home() / "Library" / "Services"
# Every workflow Wemute installs carries this in its Info.plist, so removal
# never touches Quick Actions the user made.
MARKER = "WemuteQuickAction"


@dataclass(frozen=True, slots=True)
class QuickAction:
    key: str
    title: tuple[str, str]  # (zh, en)
    action: str = ""  # Wemute --cli --action id; "" = default formats
    opens_window: bool = False
    needs_thundertalk: bool = False


QUICK_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction("open", ("用 Wemute 转换…", "Convert with Wemute…"), opens_window=True),
    QuickAction("defaults", ("Wemute：按默认格式转换", "Wemute: Convert to Default Formats")),
    QuickAction("remove_background", ("Wemute：去背景", "Wemute: Remove Background"), "remove_background"),
    QuickAction("to_pdf", ("Wemute：转成 PDF", "Wemute: Convert to PDF"), "to_pdf"),
    QuickAction("subtitles", ("Wemute：生成字幕", "Wemute: Make Subtitles"), "subtitles_srt", needs_thundertalk=True),
)


def wemute_command() -> list[str]:
    """How a Quick Action starts Wemute: the app binary, or Python from source."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "wemute"]


def _script(quick: QuickAction, command: list[str], bundle: Path | None) -> str:
    if quick.opens_window:
        if bundle is not None:
            return f'open -a {shlex.quote(str(bundle))} "$@"'
        return f'{shlex.join(command)} "$@" >/dev/null 2>&1 &'
    action = f" --action {shlex.quote(quick.action)}" if quick.action else ""
    return f'{shlex.join(command)} --cli convert --notify{action} "$@" >/dev/null 2>&1'


def _workflow(script: str) -> dict:
    """The document.wflow of a one-step Quick Action that receives files in Finder."""
    arguments = {
        str(index): {"default value": default, "name": name, "required": "0", "type": "0", "uuid": str(index)}
        for index, (name, default) in enumerate(
            [
                ("inputMethod", 0),
                ("CheckedForUserDefaultShell", False),
                ("source", ""),
                ("COMMAND_STRING", ""),
                ("shell", "/bin/sh"),
            ]
        )
    }
    action = {
        "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
        "AMActionVersion": "2.0.3",
        "AMApplication": ["Automator"],
        "AMParameterProperties": {key: {} for key in ("COMMAND_STRING", "CheckedForUserDefaultShell", "inputMethod", "shell", "source")},
        "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
        "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
        "ActionName": "Run Shell Script",
        "ActionParameters": {
            "COMMAND_STRING": script,
            "CheckedForUserDefaultShell": True,
            "inputMethod": 1,  # files as arguments
            "shell": "/bin/zsh",
            "source": "",
        },
        "BundleIdentifier": "com.apple.RunShellScript",
        "CFBundleVersion": "2.0.3",
        "CanShowSelectedItemsWhenRun": False,
        "CanShowWhenRun": True,
        "Category": ["AMCategoryUtilities"],
        "Class Name": "RunShellScriptAction",
        "InputUUID": str(uuid.uuid4()).upper(),
        "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
        "OutputUUID": str(uuid.uuid4()).upper(),
        "UUID": str(uuid.uuid4()).upper(),
        "UnlocalizedApplications": ["Automator"],
        "arguments": arguments,
        "conversionLabel": 0,
        "isViewVisible": 1,
        "location": "309.000000:305.000000",
        "nibPath": "/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib",
    }
    finder = "/System/Library/CoreServices/Finder.app"
    return {
        "AMApplicationBuild": "534",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [{"action": action, "isViewVisible": 1}],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleID": "com.apple.finder",
            "applicationBundleIDsByPath": {finder: "com.apple.finder"},
            "applicationPath": finder,
            "applicationPaths": [finder],
            "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "outputTypeIdentifier": "com.apple.Automator.nothing",
            "presentationMode": 15,
            "processesInput": False,
            "serviceApplicationBundleID": "com.apple.finder",
            "serviceApplicationPath": finder,
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": False,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": False,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def _info(title: str) -> dict:
    return {
        MARKER: True,
        "NSServices": [
            {
                "NSBackgroundColorName": "background",
                "NSIconName": "NSActionTemplate",
                "NSMenuItem": {"default": title},
                "NSMessage": "runWorkflowAsService",
                "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
                "NSSendFileTypes": ["public.item"],
            }
        ],
    }


def _ours(bundle: Path) -> bool:
    try:
        with (bundle / "Contents" / "Info.plist").open("rb") as stream:
            return plistlib.load(stream).get(MARKER) is True
    except (OSError, ValueError, plistlib.InvalidFileException):
        return False


def installed(services: Path = SERVICES) -> list[Path]:
    if not services.is_dir():
        return []
    return sorted(path for path in services.glob("*.workflow") if _ours(path))


def install(
    language: str,
    *,
    thundertalk: bool,
    command: list[str] | None = None,
    app_bundle: Path | None = None,
    services: Path = SERVICES,
) -> list[Path]:
    """(Re)install every Quick Action in ``language``; returns the workflow paths."""
    remove(services)
    command = command or wemute_command()
    zh = language == "zh"
    written: list[Path] = []
    for quick in QUICK_ACTIONS:
        if quick.needs_thundertalk and not thundertalk:
            continue
        title = quick.title[0] if zh else quick.title[1]
        bundle = services / f"{title.rstrip('…').replace('/', '-').replace(':', ' -')}.workflow"
        contents = bundle / "Contents"
        contents.mkdir(parents=True, exist_ok=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps(_info(title)))
        (contents / "document.wflow").write_bytes(
            plistlib.dumps(_workflow(_script(quick, command, app_bundle)))
        )
        written.append(bundle)
    refresh_services()
    return written


def remove(services: Path = SERVICES) -> int:
    removed = 0
    for bundle in installed(services):
        shutil.rmtree(bundle, ignore_errors=True)
        removed += 1
    if removed:
        refresh_services()
    return removed


def refresh_services() -> None:
    """Ask macOS to re-read ~/Library/Services so Finder shows the change now."""
    pbs = Path("/System/Library/CoreServices/pbs")
    if pbs.exists():
        try:
            subprocess.run([str(pbs), "-update"], capture_output=True, timeout=20, check=False)
        except (OSError, subprocess.SubprocessError):
            pass


def app_bundle_path() -> Path | None:
    """The running Wemute.app, when packaged."""
    if not getattr(sys, "frozen", False):
        return None
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    return None
