"""The `wemute` agent skill: teaches Claude Code, Codex and other agents to use Wemute.

Installed from 设置 · 集成. The skill (assets/skill/SKILL.md) is copied into
every agent skills folder this Mac has, with the command that runs Wemute
here written in, so agents read and convert files with ``wemute extract`` and
``wemute convert`` instead of writing their own parsers.
"""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path

from wemute import command_line
from wemute.paths import ASSET_ROOT

TEMPLATE = ASSET_ROOT / "skill" / "SKILL.md"
MARKER = "<!-- Installed by Wemute (Settings › Integrations) -->"
NAME = "wemute"


def skill_roots(home: Path | None = None) -> list[Path]:
    """Skills folders of the agents installed here: Claude Code, Codex, and the shared ~/.agents."""
    home = home or Path.home()
    roots = []
    for agent_dir, skills in ((".claude", "skills"), (".codex", "skills"), (".agents", "skills")):
        if (home / agent_dir).is_dir():
            roots.append(home / agent_dir / skills)
    return roots


def command_text(app_command: list[str]) -> str:
    """How an agent's shell should start Wemute on this Mac."""
    shim = command_line.installed_path()
    if shim is not None:
        on_path = str(shim.parent) in os.environ.get("PATH", "").split(os.pathsep)
        return "wemute" if on_path else str(shim)
    return shlex.join(app_command) + " --cli"


def render(app_command: list[str]) -> str:
    text = TEMPLATE.read_text(encoding="utf-8").replace("{{WEMUTE}}", command_text(app_command))
    return text.rstrip() + "\n\n" + MARKER + "\n"


def _ours(folder: Path) -> bool:
    try:
        return MARKER in (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def installed(home: Path | None = None) -> list[Path]:
    return [root / NAME for root in skill_roots(home) if _ours(root / NAME)]


def install(app_command: list[str], home: Path | None = None) -> list[Path]:
    roots = skill_roots(home)
    if not roots:
        raise FileNotFoundError("No AI agent found on this Mac (looked for ~/.claude, ~/.codex and ~/.agents)")
    text = render(app_command)
    written = []
    for root in roots:
        folder = root / NAME
        if folder.exists() and not _ours(folder):
            continue  # someone's own "wemute" skill: leave it alone
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(text, encoding="utf-8")
        written.append(folder)
    return written


def remove(home: Path | None = None) -> int:
    folders = installed(home)
    for folder in folders:
        shutil.rmtree(folder)
    return len(folders)
