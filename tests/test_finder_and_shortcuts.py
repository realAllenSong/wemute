from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from wemute import finder_actions, shortcut_file


@pytest.fixture(autouse=True)
def _no_pbs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(finder_actions, "refresh_services", lambda: None)


def test_install_writes_quick_actions_and_remove_spares_others(tmp_path: Path) -> None:
    mine = tmp_path / "My Own.workflow" / "Contents"
    mine.mkdir(parents=True)
    (mine / "Info.plist").write_bytes(plistlib.dumps({"NSServices": []}))

    written = finder_actions.install("zh", thundertalk=False, command=["/x/Wemute"], services=tmp_path)
    names = {path.name for path in written}
    assert "Wemute：去背景.workflow" in names
    assert not any("字幕" in name for name in names)  # needs ThunderTalk

    workflow = plistlib.loads((tmp_path / "Wemute：去背景.workflow" / "Contents" / "document.wflow").read_bytes())
    script = workflow["actions"][0]["action"]["ActionParameters"]["COMMAND_STRING"]
    assert script.startswith("/x/Wemute --cli convert --notify --action remove_background")
    assert workflow["workflowMetaData"]["workflowTypeIdentifier"] == "com.apple.Automator.servicesMenu"
    info = plistlib.loads((tmp_path / "Wemute：去背景.workflow" / "Contents" / "Info.plist").read_bytes())
    assert info["NSServices"][0]["NSMenuItem"]["default"] == "Wemute：去背景"

    again = finder_actions.install("en", thundertalk=True, command=["/x/Wemute"], services=tmp_path)
    assert any("Subtitles" in path.name for path in again)
    assert len(finder_actions.installed(tmp_path)) == len(again)  # zh copies replaced

    assert finder_actions.remove(tmp_path) == len(again)
    assert (tmp_path / "My Own.workflow").is_dir()


def test_open_action_uses_the_app_bundle(tmp_path: Path) -> None:
    finder_actions.install("en", thundertalk=False, command=["/x/Wemute"],
                           app_bundle=Path("/Applications/Wemute.app"), services=tmp_path)
    workflow = plistlib.loads((tmp_path / "Convert with Wemute.workflow" / "Contents" / "document.wflow").read_bytes())
    assert workflow["actions"][0]["action"]["ActionParameters"]["COMMAND_STRING"] == 'open -a /Applications/Wemute.app "$@"'


def test_shortcut_runs_wemute_on_its_input() -> None:
    plist = shortcut_file.shortcut_plist(["/Applications/Wemute.app/Contents/MacOS/Wemute"])
    step = plist["WFWorkflowActions"][0]
    assert step["WFWorkflowActionIdentifier"] == "is.workflow.actions.runshellscript"
    parameters = step["WFWorkflowActionParameters"]
    assert parameters["InputMode"] == "as arguments"
    assert "--cli convert --notify --plain" in parameters["Script"]
    assert parameters["Input"]["Value"]["Type"] == "ExtensionInput"
