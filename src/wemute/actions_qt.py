from __future__ import annotations

from PySide6.QtCore import Property, QMetaObject, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from wemute.actions import (
    TAGS,
    ACTION_BY_ID,
    Action,
    availability,
    category_for,
    hint_for,
    menu_tree,
    search,
    text,
)
from wemute.ai_packages_qt import AIModelController
from wemute.controller import JobController
from wemute.i18n import I18n
from wemute.settings_qt import AppSettings
from wemute.tools import thundertalk_available, vision_available
from wemute.updater import SparkleUpdater


def focused_text_input() -> QObject | None:
    """The text field with keyboard focus, so Edit commands reach it first."""
    focus = QGuiApplication.focusObject()
    if focus is None:
        return None
    meta = focus.metaObject()
    if meta.indexOfMethod("paste()") >= 0 and meta.indexOfProperty("cursorPosition") >= 0:
        return focus
    return None


def forward_to_text(method: str) -> bool:
    target = focused_text_input()
    if target is None:
        return False
    QMetaObject.invokeMethod(target, method)
    return True


class ActionCenter(QObject):
    """The 工具 menu, the menu bar's Tools menu and ⌘K share these actions."""

    menuChanged = Signal()
    # Handled by the window: "add_files", "settings:<page>", "palette", "tools",
    # "shortcuts", "privacy".
    commandRequested = Signal(str)

    def __init__(
        self,
        controller: JobController,
        settings: AppSettings,
        i18n: I18n,
        ai_models: AIModelController | None = None,
        updater: SparkleUpdater | None = None,
    ) -> None:
        super().__init__()
        self.controller = controller
        self.settings = settings
        self.i18n = i18n
        self.updater = updater
        i18n.languageChanged.connect(self.menuChanged)
        if ai_models is not None:
            ai_models.catalogChanged.connect(self.menuChanged)

    @property
    def language(self) -> str:
        return self.i18n.language

    def check(self, action: Action) -> str:
        return availability(
            self.controller.model.enabled_ai_actions,
            vision_available(),
            bool(self.updater and self.updater.available),
            thundertalk_available(),
        )(action)

    def tree(self) -> list[dict[str, object]]:
        return menu_tree(self.language, self.check)

    @Property("QVariantList", notify=menuChanged)
    def menu(self) -> list[dict[str, object]]:
        return self.tree()

    @Slot(str, result="QVariantList")
    def search(self, query: str) -> list[dict[str, object]]:
        language = self.language
        rows: list[dict[str, object]] = []
        for action in search(query, language, self.check):
            rows.append(
                {
                    "id": action.id,
                    "label": text(action.palette_title or action.title, language),
                    "category": category_for(action, language),
                    "icon": action.icon,
                    "tint": action.tint,
                    "shortcut": action.shortcut,
                    "available": self.check(action) == "",
                    "tag": TAGS.get(self.check(action), ""),
                }
            )
        return rows

    @Slot(str, result=str)
    def title(self, action_id: str) -> str:
        action = ACTION_BY_ID.get(action_id)
        return text(action.title, self.language) if action else ""

    @Slot(str)
    def run(self, action_id: str) -> None:
        action = ACTION_BY_ID.get(action_id)
        if action is None:
            return
        state = self.check(action)
        if state == "hidden":
            return
        if action.command:
            self.run_command(action.command)
            return
        if state == "needs_app":
            name = text(action.palette_title or action.title, self.language).rstrip("…")
            self.controller.notify(self.i18n.t("action_needs_thundertalk").replace("{name}", name))
            self.commandRequested.emit("settings:integrations")
            return
        if state == "missing":
            name = text(action.palette_title or action.title, self.language).rstrip("…")
            self.controller.notify(self.i18n.t("action_needs_model").replace("{name}", name))
            self.commandRequested.emit("settings:components")
            return
        self.controller.apply_action(dict(action.choices), hint_for(action, self.language))

    def run_command(self, command: str) -> None:
        if command == "paste":
            if not forward_to_text("paste"):
                self.controller.pasteFiles()
        elif command == "undo":
            if not forward_to_text("undo"):
                self.controller.undoClear()
        elif command == "clear":
            # ⌘⌫ inside a text field deletes text there, never the file list.
            if focused_text_input() is None:
                self.controller.clearWithUndo()
        elif command == "start":
            if self.controller.phase == "ready":
                self.controller.startAll()
        elif command == "reveal":
            self.controller.revealOutputs()
        elif command.startswith("appearance:"):
            self.settings.setAppearance(command.partition(":")[2])
        elif command == "reduce_motion":
            self.settings.toggleReduceMotion()
        elif command == "updates":
            if self.updater:
                self.updater.checkForUpdates()
        else:
            self.commandRequested.emit(command)
