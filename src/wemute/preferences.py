"""App-wide preferences that are not about conversions: appearance, motion,
session restore and window placement. Stored as JSON next to the queue."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

APPEARANCES = ("system", "light", "dark")


@dataclass(slots=True)
class Preferences:
    appearance: str = "system"
    reduce_motion: bool = False
    restore_session: bool = True
    # name → [x, y, width, height]
    windows: dict[str, list[int]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: object) -> "Preferences":
        if not isinstance(payload, dict):
            return cls()
        appearance = payload.get("appearance")
        windows: dict[str, list[int]] = {}
        raw_windows = payload.get("windows")
        if isinstance(raw_windows, dict):
            for name, value in raw_windows.items():
                if (
                    isinstance(value, list)
                    and len(value) == 4
                    and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
                    and value[2] > 0
                    and value[3] > 0
                ):
                    windows[str(name)] = list(value)
        return cls(
            appearance=appearance if appearance in APPEARANCES else "system",
            reduce_motion=payload.get("reduce_motion") is True,
            restore_session=payload.get("restore_session") is not False,
            windows=windows,
        )


class PreferenceStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Preferences:
        try:
            return Preferences.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return Preferences()

    def save(self, preferences: Preferences) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(asdict(preferences), indent=2), encoding="utf-8")
            os.replace(temporary, self.path)
        except OSError:
            pass


def resolve_dark(appearance: str, system_dark: bool) -> bool:
    """Whether the UI draws dark for an appearance choice and the system's own."""
    if appearance == "dark":
        return True
    if appearance == "light":
        return False
    return system_dark
