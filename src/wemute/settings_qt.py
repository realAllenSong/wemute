from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

from wemute import finder_actions, shortcut_file
from wemute.integrations import detect_app, thundertalk_app, thundertalk_cli_version
from wemute.paths import CACHE_ROOT
from wemute.preferences import APPEARANCES, Preferences, PreferenceStore


def apply_color_scheme(appearance: str) -> None:
    """Light or dark for the whole app, native menus and title bars included."""
    app = QGuiApplication.instance()
    if app is None:
        return
    hints = app.styleHints()
    if appearance == "light":
        hints.setColorScheme(Qt.ColorScheme.Light)
    elif appearance == "dark":
        hints.setColorScheme(Qt.ColorScheme.Dark)
    else:
        hints.unsetColorScheme()


class AppSettings(QObject):
    """设置 · 通用 and 外观, plus where the settings window was left."""

    appearanceChanged = Signal()
    preferencesChanged = Signal()

    def __init__(
        self,
        store: PreferenceStore,
        apply_scheme: Callable[[str], None] = apply_color_scheme,
    ) -> None:
        super().__init__()
        self._store = store
        self._apply_scheme = apply_scheme
        self._preferences = store.load()
        # --appearance for screenshots: this session only, never saved.
        self._session_appearance = ""
        self._apply_scheme(self.appearance)

    def _save(self) -> None:
        self._store.save(self._preferences)

    @Property(str, notify=appearanceChanged)
    def appearance(self) -> str:
        return self._session_appearance or self._preferences.appearance

    @Slot(str)
    def setAppearance(self, appearance: str) -> None:
        if appearance not in APPEARANCES:
            return
        self._session_appearance = ""
        self._preferences.appearance = appearance
        self._save()
        self._apply_scheme(appearance)
        self.appearanceChanged.emit()

    def override_appearance(self, appearance: str) -> None:
        if appearance in APPEARANCES:
            self._session_appearance = appearance
            self._apply_scheme(appearance)
            self.appearanceChanged.emit()

    @Property(bool, notify=preferencesChanged)
    def reduceMotion(self) -> bool:
        return self._preferences.reduce_motion

    @reduceMotion.setter
    def reduceMotion(self, value: bool) -> None:
        if bool(value) == self._preferences.reduce_motion:
            return
        self._preferences.reduce_motion = bool(value)
        self._save()
        self.preferencesChanged.emit()

    @Slot()
    def toggleReduceMotion(self) -> None:
        self.reduceMotion = not self.reduceMotion

    @Property(bool, notify=preferencesChanged)
    def restoreSession(self) -> bool:
        return self._preferences.restore_session

    @restoreSession.setter
    def restoreSession(self, value: bool) -> None:
        if bool(value) == self._preferences.restore_session:
            return
        self._preferences.restore_session = bool(value)
        self._save()
        self.preferencesChanged.emit()

    @Slot(str, result="QVariantList")
    def windowGeometry(self, name: str) -> list[int]:
        return list(self._preferences.windows.get(name, []))

    @Slot(str, int, int, int, int)
    def saveWindowGeometry(self, name: str, x: int, y: int, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        value = [int(x), int(y), int(width), int(height)]
        if self._preferences.windows.get(name) != value:
            self._preferences.windows[name] = value
            self._save()

    @Slot()
    def reset(self) -> None:
        windows = self._preferences.windows
        self._preferences = Preferences(windows=windows)
        self._session_appearance = ""
        self._save()
        self._apply_scheme(self.appearance)
        self.appearanceChanged.emit()
        self.preferencesChanged.emit()


class Integrations(QObject):
    """设置 · 集成: what is available today and what is still to come."""

    changed = Signal()

    def __init__(self, thundertalk: Path | None = None, language=None) -> None:  # noqa: ANN001
        super().__init__()
        self._language = language or (lambda: "en")
        self._error = ""
        self._thundertalk_path = thundertalk or thundertalk_app()
        self._thundertalk = self._probe()

    def _probe(self) -> dict[str, object]:
        detected = detect_app(self._thundertalk_path)
        detected["cli"] = bool(detected["installed"]) and thundertalk_cli_version(self._thundertalk_path) >= 1
        return detected

    @Property("QVariantMap", notify=changed)
    def thunderTalk(self) -> dict[str, object]:
        return dict(self._thundertalk)

    @Property(bool, constant=True)
    def finderActionAvailable(self) -> bool:
        return sys.platform == "darwin"

    @Property(bool, constant=True)
    def shortcutsAvailable(self) -> bool:
        return shortcut_file.available()

    @Property(bool, notify=changed)
    def finderActionsInstalled(self) -> bool:
        return bool(finder_actions.installed())

    @Property(str, notify=changed)
    def lastError(self) -> str:
        return self._error

    @Slot()
    def installFinderActions(self) -> None:
        try:
            finder_actions.install(
                self._language(),
                thundertalk=bool(self._thundertalk.get("cli")),
                app_bundle=finder_actions.app_bundle_path(),
            )
            self._error = ""
        except OSError as exc:
            self._error = str(exc)
        self.changed.emit()

    @Slot()
    def removeFinderActions(self) -> None:
        finder_actions.remove()
        self.changed.emit()

    @Slot()
    def installShortcut(self) -> None:
        """Sign the shortcut and open it; Shortcuts asks the user to add it."""
        try:
            signed = shortcut_file.build_signed(
                finder_actions.wemute_command(), CACHE_ROOT / "shortcut", self._language()
            )
            self._error = ""
            QProcess.startDetached("/usr/bin/open", [str(signed)])
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._error = str(exc)
        self.changed.emit()

    @Slot(result=str)
    def cliCommand(self) -> str:
        """For 「复制命令」: what to paste into a Run Shell Script action."""
        return shlex.join(finder_actions.wemute_command()) + ' --cli convert --action remove_background "$@"'

    @Slot()
    def refresh(self) -> None:
        detected = self._probe()
        if detected != self._thundertalk:
            self._thundertalk = detected
            self.changed.emit()

    @Slot()
    def openThunderTalk(self) -> None:
        if self._thundertalk.get("installed"):
            QProcess.startDetached("/usr/bin/open", [str(self._thundertalk_path)])
