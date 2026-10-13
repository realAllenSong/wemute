"""The macOS menu bar: Wemute · 文件 · 编辑 · 显示 · 工具 · 窗口 · 帮助.

A QMenuBar without a parent becomes the system menu bar on macOS. Items for
the application menu (关于, 设置…, 退出) are placed by their menu role.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTranslator, Qt
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar

from wemute.actions import ACTION_BY_ID, text
from wemute.actions_qt import ActionCenter, forward_to_text
from wemute.controller import JobController
from wemute.i18n import I18n
from wemute.settings_qt import AppSettings

# Qt names the items it adds to the application menu in this context.
_APP_MENU = {
    "zh": {
        "Services": "服务",
        "Hide %1": "隐藏 %1",
        "Hide Others": "隐藏其他",
        "Show All": "全部显示",
        "Preferences...": "设置…",
        "Settings...": "设置…",
        "Settings…": "设置…",
        "Quit %1": "退出 %1",
        "About %1": "关于 %1",
    },
    "en": {"Preferences...": "Settings…", "Settings...": "Settings…"},
}


class AppMenuTranslator(QTranslator):
    def __init__(self, language: Callable[[], str]) -> None:
        super().__init__()
        self._language = language

    def translate(self, context, source_text, disambiguation=None, n=-1):  # noqa: ANN001, N802
        if context != "MAC_APPLICATION_MENU":
            return ""
        return _APP_MENU.get(self._language(), {}).get(source_text, "")

    def isEmpty(self) -> bool:  # noqa: N802 - Qt API
        return False


_MENU_TEXT = {
    "zh": {
        "file": "文件", "edit": "编辑", "view": "显示", "tools": "工具", "window": "窗口", "help": "帮助",
        "undo": "撤销", "redo": "重做", "cut": "剪切", "copy": "拷贝", "select_all": "全选",
        "remove_selected": "移除所选文件", "appearance": "外观", "follow_system": "跟随系统",
        "light": "浅色", "dark": "深色", "search": "搜索全部功能…", "minimize": "最小化", "zoom": "缩放",
        "close": "关闭窗口", "main_window": "Wemute", "settings_window": "设置",
        "quit": "退出 Wemute",
    },
    "en": {
        "file": "File", "edit": "Edit", "view": "View", "tools": "Tools", "window": "Window", "help": "Help",
        "undo": "Undo", "redo": "Redo", "cut": "Cut", "copy": "Copy", "select_all": "Select All",
        "remove_selected": "Remove Selected File", "appearance": "Appearance", "follow_system": "System",
        "light": "Light", "dark": "Dark", "search": "Search All Actions…", "minimize": "Minimize", "zoom": "Zoom",
        "close": "Close Window", "main_window": "Wemute", "settings_window": "Settings",
        "quit": "Quit Wemute",
    },
}


class NativeMenuBar(QObject):
    def __init__(
        self,
        center: ActionCenter,
        controller: JobController,
        settings: AppSettings,
        i18n: I18n,
    ) -> None:
        super().__init__()
        self.center = center
        self.controller = controller
        self.settings = settings
        self.i18n = i18n
        self.translator = AppMenuTranslator(lambda: self.i18n.language)
        QApplication.installTranslator(self.translator)
        self.bar = QMenuBar(None)
        self._appearance_actions: dict[str, QAction] = {}
        self._reduce_motion: QAction | None = None
        self._reveal: QAction | None = None
        self._clear: QAction | None = None
        self.rebuild()
        center.menuChanged.connect(self.rebuild)
        settings.appearanceChanged.connect(self._sync_checks)
        settings.preferencesChanged.connect(self._sync_checks)

    # ------------------------------------------------------------ helpers

    def _t(self, key: str) -> str:
        return _MENU_TEXT.get(self.i18n.language, _MENU_TEXT["en"])[key]

    def _add(
        self,
        menu: QMenu,
        label: str,
        handler: Callable[[], None],
        shortcut: QKeySequence | str | None = None,
        role: QAction.MenuRole = QAction.MenuRole.NoRole,
    ) -> QAction:
        action = QAction(label, menu)
        action.setMenuRole(role)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        action.triggered.connect(lambda _checked=False: handler())
        menu.addAction(action)
        return action

    def _registry(self, menu: QMenu, action_id: str, role: QAction.MenuRole = QAction.MenuRole.NoRole) -> QAction:
        definition = ACTION_BY_ID[action_id]
        return self._add(
            menu,
            text(definition.title, self.i18n.language),
            lambda: self.center.run(action_id),
            definition.shortcut or None,
            role,
        )

    def _header(self, menu: QMenu, label: str) -> None:
        if not menu.isEmpty():
            menu.addSeparator()
        header = QAction(label, menu)
        header.setEnabled(False)
        header.setMenuRole(QAction.MenuRole.NoRole)
        menu.addAction(header)

    def _fill(self, menu: QMenu, rows: list[dict[str, object]]) -> None:
        for row in rows:
            kind = row["type"]
            if kind == "header":
                self._header(menu, str(row["label"]))
            elif kind == "menu":
                child = menu.addMenu(str(row["label"]))
                self._fill(child, list(row["children"]))  # type: ignore[arg-type]
            elif kind == "action":
                action_id = str(row["id"])
                self._add(menu, str(row["label"]), lambda action_id=action_id: self.center.run(action_id))

    @staticmethod
    def _focus_window():
        return QGuiApplication.focusWindow() or next(iter(QGuiApplication.topLevelWindows()), None)

    # ------------------------------------------------------------- build

    def rebuild(self) -> None:
        self.bar.clear()
        for menu in self.bar.findChildren(QMenu, options=Qt.FindChildOption.FindDirectChildrenOnly):
            menu.deleteLater()
        self._appearance_actions.clear()

        file_menu = self.bar.addMenu(self._t("file"))
        self._registry(file_menu, "add_files")
        self._registry(file_menu, "paste")
        self._clear = self._registry(file_menu, "clear")
        file_menu.addSeparator()
        self._reveal = self._registry(file_menu, "reveal")
        file_menu.aboutToShow.connect(self._sync_file_menu)
        # Moved into the application menu by their roles.
        self._registry(file_menu, "settings", QAction.MenuRole.PreferencesRole)
        self._add(file_menu, self._t("quit"), QApplication.quit, QKeySequence.StandardKey.Quit,
                  QAction.MenuRole.QuitRole)

        edit_menu = self.bar.addMenu(self._t("edit"))
        self._add(edit_menu, self._t("undo"), lambda: self.center.run_command("undo"), QKeySequence.StandardKey.Undo)
        self._add(edit_menu, self._t("redo"), lambda: forward_to_text("redo"), QKeySequence.StandardKey.Redo)
        edit_menu.addSeparator()
        self._add(edit_menu, self._t("cut"), lambda: forward_to_text("cut"), QKeySequence.StandardKey.Cut)
        self._add(edit_menu, self._t("copy"), lambda: forward_to_text("copy"), QKeySequence.StandardKey.Copy)
        self._add(edit_menu, self._t("select_all"), lambda: forward_to_text("selectAll"),
                  QKeySequence.StandardKey.SelectAll)
        edit_menu.addSeparator()
        self._add(edit_menu, self._t("remove_selected"), self.controller.removeSelected)

        view_menu = self.bar.addMenu(self._t("view"))
        appearance_menu = view_menu.addMenu(self._t("appearance"))
        group = QActionGroup(appearance_menu)
        for mode, key in (("system", "follow_system"), ("light", "light"), ("dark", "dark")):
            action = self._add(appearance_menu, self._t(key), lambda mode=mode: self.settings.setAppearance(mode))
            action.setCheckable(True)
            group.addAction(action)
            self._appearance_actions[mode] = action
        self._reduce_motion = self._registry(view_menu, "reduce_motion")
        self._reduce_motion.setCheckable(True)

        tools_menu = self.bar.addMenu(self._t("tools"))
        self._add(tools_menu, self._t("search"), lambda: self.center.commandRequested.emit("palette"), "Ctrl+K")
        self._fill(tools_menu, self.center.tree())

        window_menu = self.bar.addMenu(self._t("window"))
        self._add(window_menu, self._t("minimize"), self._minimize, "Ctrl+M")
        self._add(window_menu, self._t("zoom"), self._zoom)
        self._add(window_menu, self._t("close"), self._close, QKeySequence.StandardKey.Close)
        window_menu.addSeparator()
        self._add(window_menu, self._t("main_window"), lambda: self.center.commandRequested.emit("main_window"))
        self._add(window_menu, self._t("settings_window"),
                  lambda: self.center.commandRequested.emit("settings:general"))

        help_menu = self.bar.addMenu(self._t("help"))
        self._registry(help_menu, "shortcuts")
        self._registry(help_menu, "privacy")
        self._registry(help_menu, "about", QAction.MenuRole.AboutRole)
        if self.center.check(ACTION_BY_ID["updates"]) == "":
            self._registry(help_menu, "updates", QAction.MenuRole.ApplicationSpecificRole)
        self._sync_checks()

    # ------------------------------------------------------------ state

    def _sync_checks(self) -> None:
        for mode, action in self._appearance_actions.items():
            action.setChecked(mode == self.settings.appearance)
        if self._reduce_motion is not None:
            self._reduce_motion.setChecked(self.settings.reduceMotion)

    def _sync_file_menu(self) -> None:
        if self._reveal is not None:
            self._reveal.setEnabled(self.controller.succeededCount > 0)
        if self._clear is not None:
            self._clear.setEnabled(self.controller.hasJobs and not self.controller.busy)

    def _minimize(self) -> None:
        window = self._focus_window()
        if window:
            window.showMinimized()

    def _zoom(self) -> None:
        window = self._focus_window()
        if window:
            window.showNormal() if window.visibility() == window.Visibility.Maximized else window.showMaximized()

    def _close(self) -> None:
        window = QGuiApplication.focusWindow()
        if window:
            window.close()

    def titles(self) -> list[str]:
        return [action.text() for action in self.bar.actions()]
