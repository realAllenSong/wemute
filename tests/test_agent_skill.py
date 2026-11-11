"""The agent skill installs into each agent's skills folder and teaches the real command."""

from __future__ import annotations

from pathlib import Path

from wemute import agent_skill


def _home(tmp_path: Path) -> Path:
    for agent in (".claude", ".codex"):
        (tmp_path / agent).mkdir()
    return tmp_path


def test_install_writes_one_skill_per_agent_with_this_macs_command(tmp_path: Path, monkeypatch) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(agent_skill.command_line, "installed_path", lambda: None)
    written = agent_skill.install(["/Applications/Wemute.app/Contents/MacOS/Wemute"], home)

    assert written == [home / ".claude/skills/wemute", home / ".codex/skills/wemute"]
    text = (written[0] / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: wemute\ndescription: ")
    assert "`/Applications/Wemute.app/Contents/MacOS/Wemute --cli`" in text
    assert "{{WEMUTE}}" not in text
    assert agent_skill.installed(home) == written

    assert agent_skill.remove(home) == 2
    assert agent_skill.installed(home) == []
    assert not (home / ".claude/skills/wemute").exists()


def test_a_skill_the_user_wrote_is_never_overwritten(tmp_path: Path) -> None:
    home = _home(tmp_path)
    own = home / ".claude/skills/wemute"
    own.mkdir(parents=True)
    (own / "SKILL.md").write_text("my own notes", encoding="utf-8")

    written = agent_skill.install(["wemute-app"], home)

    assert written == [home / ".codex/skills/wemute"]
    assert (own / "SKILL.md").read_text(encoding="utf-8") == "my own notes"
    agent_skill.remove(home)
    assert (own / "SKILL.md").exists()


def test_the_skill_names_only_tool_ids_wemute_has() -> None:
    import re

    from wemute.actions import ACTIONS

    ids = {action.id for action in ACTIONS}
    text = agent_skill.TEMPLATE.read_text(encoding="utf-8")
    named = set(re.findall(r"`((?:format:[^`]+)|[a-z_0-9]+)`", text))
    tools = {name for name in named if name in ids or name.startswith("format:") or "_" in name}
    tools -= {"not_found", "component_missing", "thundertalk_missing", "thundertalk_outdated", "no_speech", "no_model"}
    missing = sorted(tools - ids)
    assert not missing, missing
