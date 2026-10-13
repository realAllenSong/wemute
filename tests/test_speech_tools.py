from __future__ import annotations

import json
import plistlib
import stat
from pathlib import Path

import pytest

from wemute import integrations
from wemute.domain import MediaKind
from wemute.engines import route
from wemute.engines.common import Reporter
from wemute.engines.speech import run, text_for_reading
from wemute.tools import TOOL_BY_KEY, tools_for


def _bundle(root: Path, *, plist_key: bool, cli_module: bool) -> Path:
    bundle = root / "ThunderTalk.app"
    macos = bundle / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    info = {"CFBundleShortVersionString": "1.9.3"}
    if plist_key:
        info[integrations.CLI_PLIST_KEY] = 1
    (bundle / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))
    (macos / "ThunderTalk").write_bytes(b"\0" * 5000 + (b"thundertalk.cli" if cli_module else b"") + b"\0" * 10)
    return bundle


def test_cli_support_from_plist_key_or_binary(tmp_path: Path) -> None:
    assert integrations.thundertalk_cli_version(_bundle(tmp_path / "a", plist_key=True, cli_module=False)) == 1
    assert integrations.thundertalk_cli_version(_bundle(tmp_path / "b", plist_key=False, cli_module=True)) == 1
    assert integrations.thundertalk_cli_version(_bundle(tmp_path / "c", plist_key=False, cli_module=False)) == 0
    assert integrations.thundertalk_cli_version(tmp_path / "missing.app") == 0


def test_speech_tools_follow_thundertalk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old = _bundle(tmp_path / "old", plist_key=False, cli_module=False)
    monkeypatch.setenv("WEMUTE_THUNDERTALK_APP", str(old))
    assert "Subtitles SRT" not in {tool.key for tool in tools_for(MediaKind.VIDEO)}
    new = _bundle(tmp_path / "new", plist_key=True, cli_module=True)
    monkeypatch.setenv("WEMUTE_THUNDERTALK_APP", str(new))
    keys = {tool.key for tool in tools_for(MediaKind.VIDEO)}
    assert {"Subtitles SRT", "Subtitles VTT", "Transcript TXT"} <= keys
    assert "Read aloud M4A" in {tool.key for tool in tools_for(MediaKind.DATA)}
    assert route(MediaKind.VIDEO, ".mp4", "Subtitles SRT").lane == "speech"
    assert TOOL_BY_KEY["Subtitles SRT"].needs == "thundertalk"


def test_text_for_reading_strips_markup(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    md.write_text("# 周报\n\n本周完成了 **Wemute** 的[设置](https://x.y)。\n\n```py\ncode\n```\n", encoding="utf-8")
    text = text_for_reading(md, ".md")
    assert "周报" in text and "Wemute" in text and "设置" in text
    assert "#" not in text and "**" not in text and "code" not in text and "https" not in text
    html = tmp_path / "page.html"
    html.write_text("<p>Hello <b>there</b></p><script>alert(1)</script><p>bye</p>", encoding="utf-8")
    assert "alert" not in text_for_reading(html, ".html")
    assert "Hello there" in text_for_reading(html, ".html")
    with pytest.raises(ValueError):
        text_for_reading(tmp_path / "x.csv", ".csv")


def _fake_cli(tmp_path: Path, lines: list[dict], code: int = 0) -> Path:
    script = tmp_path / "ThunderTalk"
    body = "\n".join(f"echo '{json.dumps(line)}'" for line in lines)
    script.write_text(f"#!/bin/sh\necho 'No Assistant asset for language xx'\n{body}\nexit {code}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def test_run_maps_progress_and_errors(tmp_path: Path) -> None:
    import io

    ok = _fake_cli(tmp_path, [
        {"type": "stage", "label": "transcribe"},
        {"type": "progress", "value": 0.5},
        {"type": "result", "ok": True, "output": "x"},
    ])
    stream = io.StringIO()
    request = {"tool": "transcribe", "options": {"format": "srt"}, "sources": ["a.mp4"],
               "output": str(tmp_path / "a.srt"), "thundertalk": str(ok)}
    run(request, Reporter("zh", stream))
    assert "wemute_stage=识别语音…" in stream.getvalue()
    assert "wemute_progress=0.5000" in stream.getvalue()

    failing = tmp_path / "fail"
    failing.mkdir()
    bad = _fake_cli(failing, [{"type": "result", "ok": False, "code": "no_speech", "error": "x"}], code=1)
    with pytest.raises(Exception, match="没有听到说话的声音"):
        run({**request, "thundertalk": str(bad)}, Reporter("zh", io.StringIO()))
