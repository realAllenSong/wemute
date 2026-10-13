"""Headless conversions for Finder Quick Actions, Shortcuts and scripts.

    Wemute --cli convert FILE… [--action ID] [--notify]
    Wemute --cli actions

``convert`` runs the same queue as the window: each file gets the user's
default format for its kind (设置 · 转换 · 默认格式), or the tool named by
``--action`` (an id from the 工具 menu, e.g. ``remove_bg``, ``to_pdf``,
``subtitles_srt``). Save location and naming follow the settings too. The
open window's file list is never touched.

stdout carries one JSON line per finished file and a final summary:

    {"type": "file", "source": "/a.heic", "ok": true, "output": "/a.jpg"}
    {"type": "result", "ok": true, "converted": 3, "failed": 0}

Exit status 0 when every file converted, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from wemute.domain import JobRecord, JobStatus
from wemute.persistence import QueueStore


class _ScratchStore(QueueStore):
    """Reads settings beside the real queue but never loads or saves the list."""

    def load(self) -> list[JobRecord]:
        return []

    def save(self, jobs: list[JobRecord]) -> None:
        pass


_PLAIN = False


def _emit(**event: object) -> None:
    if _PLAIN:
        # Shortcuts and shell pipelines: just the files that were made.
        if event.get("type") == "file" and event.get("ok") and event.get("output"):
            print(event["output"], flush=True)
        return
    print(json.dumps(event, ensure_ascii=False), flush=True)


def _notify(title: str, message: str) -> None:
    script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
    try:
        subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Wemute --cli")
    sub = parser.add_subparsers(dest="command", required=True)
    convert = sub.add_parser("convert", help="convert files with the default formats or one tool")
    convert.add_argument("paths", nargs="+")
    convert.add_argument("--action", default="", help="a tool id from `Wemute --cli actions`")
    convert.add_argument("--notify", action="store_true", help="show a notification when done")
    convert.add_argument("--plain", action="store_true", help="print only the output paths, one per line")
    convert.add_argument("--timeout", type=float, default=6 * 3600)
    sub.add_parser("actions", help="list tool ids for --action")
    return parser


def _language() -> str:
    from wemute.i18n import I18n

    return I18n().language


def _list_actions(language: str) -> int:
    from wemute.actions import ACTIONS, text

    for action in ACTIONS:
        if action.choices and action.section != "app":
            _emit(type="action", id=action.id, title=text(action.palette_title or action.title, language))
    return 0


def _convert(arguments: argparse.Namespace, language: str) -> int:
    from PySide6.QtCore import QTimer

    from wemute.actions import ACTION_BY_ID, hint_for
    from wemute.controller import JobController
    from wemute.queue_model import QueueModel

    zh = language == "zh"
    action = ACTION_BY_ID.get(arguments.action) if arguments.action else None
    if arguments.action and (action is None or not action.choices):
        _emit(type="result", ok=False, error=f"unknown action: {arguments.action}", code="bad_args")
        return 1

    model = QueueModel()
    model.set_language(language)
    controller = JobController(model, store=_ScratchStore())
    if action is not None:
        # Armed before the files arrive, exactly like choosing a tool first in
        # the window, so 添加后自动开始 never starts them with the defaults.
        controller.apply_action(dict(action.choices), hint_for(action, language))

    paths = [str(Path(path).expanduser().resolve()) for path in arguments.paths]
    started = time.monotonic()
    state = {"started": False, "code": 1}
    # Files the chosen tool cannot handle are left alone, never converted to a default.
    skipped: list[str] = []
    not_applicable = "这个工具不适用于此文件" if zh else "This tool doesn't apply to this file"

    def finish() -> None:
        jobs = model.jobs
        converted = [job for job in jobs if job.status == JobStatus.SUCCEEDED]
        failed = [job for job in jobs if job.status != JobStatus.SUCCEEDED]
        for source in skipped:
            _emit(type="file", source=source, ok=False, output="", error=not_applicable)
        for job in jobs:
            _emit(
                type="file",
                source=job.source.path,
                ok=job.status == JobStatus.SUCCEEDED,
                output=getattr(job, "output_path", "") or "",
                error=job.error or "",
            )
        ok = bool(converted) and not failed and not skipped
        nothing = ("没有可以转换的文件" if zh else "No files Wemute can convert") if not skipped else not_applicable
        if not jobs:
            _emit(type="result", ok=False, converted=0, failed=len(skipped), error=nothing, code="unsupported")
        else:
            _emit(type="result", ok=ok, converted=len(converted), failed=len(failed) + len(skipped))
        if arguments.notify:
            if not jobs:
                message = nothing
            elif (failed or skipped) and converted:
                missed = len(failed) + len(skipped)
                message = (f"已完成 {len(converted)} 个，{missed} 个未转换" if zh
                           else f"{len(converted)} done, {missed} not converted")
            elif failed:
                reason = failed[0].error or ""
                message = (f"转换失败：{reason}" if zh else f"Conversion failed: {reason}").rstrip("：: ")
            else:
                message = f"已完成 {len(converted)} 个文件" if zh else f"Converted {len(converted)} files"
            _notify("Wemute", message)
        state["code"] = 0 if ok else 1
        controller.shutdown()
        app.quit()

    def poll() -> None:
        if time.monotonic() - started > arguments.timeout:
            finish()
            return
        probing = controller._probing or controller._pending_paths  # noqa: SLF001 - same package
        if not state["started"]:
            if probing:
                QTimer.singleShot(200, poll)
                return
            if action is not None:
                kinds = {kind for kind, _choice in action.choices}
                for job in list(model.jobs):
                    if job.source.kind not in kinds:
                        skipped.append(job.source.path)
                        controller.removeJob(job.id)
            if not model.jobs:
                finish()
                return
            if controller.phase == "ready":
                controller.startAll()
            state["started"] = True
        elif controller.phase not in {"running"} and not controller.busy:
            finish()
            return
        QTimer.singleShot(300, poll)

    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    controller.add_paths(paths)
    QTimer.singleShot(300, poll)
    app.exec()
    return state["code"]


def main(argv: list[str]) -> int:
    arguments = _parser().parse_args(argv)
    global _PLAIN
    _PLAIN = bool(getattr(arguments, "plain", False))
    # No window, no Dock icon: the offscreen platform before Qt starts.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("Wemute")
    app.setOrganizationName("Wemute")
    language = _language()
    if arguments.command == "actions":
        return _list_actions(language)
    return _convert(arguments, language)
