from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    Q_ARG,
    QCoreApplication,
    QEvent,
    QMetaObject,
    QObject,
    QTimer,
    QUrl,
    Qt,
    Signal,
)
from PySide6.QtGui import QFileOpenEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from wemute.app_info import AppInfoController
from wemute.controller import JobController
from wemute.ai_packages_qt import AIModelController
from wemute.components import ComponentManager
from wemute.components_qt import ComponentController
from wemute.i18n import I18n
from wemute.icon_provider import NativeIconProvider, RoundedThumbnailProvider
from wemute.paths import QML_ROOT
from wemute.probe import probe_file
from wemute.queue_model import QueueModel
from wemute.model_packages import ModelPackageManager
from wemute.updater import SparkleUpdater
from wemute.actions_qt import ActionCenter
from wemute.paths import DATA_ROOT
from wemute.preferences import PreferenceStore
from wemute.settings_qt import AppSettings, Integrations
from wemute import __version__

SETTINGS_PAGES = ("general", "appearance", "convert", "components", "integrations", "about")


class WemuteApplication(QApplication):
    fileOpened = Signal(str)

    def __init__(self, arguments: list[str]) -> None:
        super().__init__(arguments)
        self.pending_file_opens: list[str] = []

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.FileOpen and isinstance(event, QFileOpenEvent):
            path = event.file() or event.url().toLocalFile()
            if path:
                self.pending_file_opens.append(path)
                self.fileOpened.emit(path)
            return True
        return super().event(event)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wemute")
    parser.add_argument("paths", nargs="*", help="Files or folders to add on launch")
    parser.add_argument("--smoke-test", action="store_true", help="Load QML and exit")
    parser.add_argument("--demo-dir", type=Path, help="Load a fixed visual QA queue")
    parser.add_argument("--screenshot", type=Path, help="Save the rendered app window")
    parser.add_argument("--screenshot-delay", type=int, default=2200, help=argparse.SUPPRESS)
    parser.add_argument("--show-image-options", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-ai-tools", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-erase-editor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-about", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-menu", metavar="KIND", help=argparse.SUPPRESS)
    parser.add_argument(
        "--show-settings", nargs="?", const="general", choices=SETTINGS_PAGES, help=argparse.SUPPRESS
    )
    parser.add_argument("--show-palette", nargs="?", const="", metavar="QUERY", help=argparse.SUPPRESS)
    parser.add_argument("--show-tools-menu", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-shortcuts", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--dump-menu", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-components", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--qa-action", choices=["start", "clear"], help=argparse.SUPPRESS)
    parser.add_argument("--qa-install-model", metavar="ID", help=argparse.SUPPRESS)
    parser.add_argument("--qa-action-delay", type=int, default=1200, help=argparse.SUPPRESS)
    parser.add_argument("--appearance", choices=["system", "light", "dark"], help=argparse.SUPPRESS)
    parser.add_argument("--language", choices=["en", "zh"], help=argparse.SUPPRESS)
    parser.add_argument("--require-updater", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--image-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ai-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ai-worker-server", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--convert-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--audio-runtime-smoke-test", action="store_true", help=argparse.SUPPRESS)
    return parser


def _demo_descriptors(directory: Path) -> list:
    preferred = [
        "Portrait.heic",
        "Field Recording.wav",
        "Product Demo.mov",
        "Surf Session.mov",
        "City Timelapse.mov",
    ]
    paths = [directory / name for name in preferred]
    return [probe_file(path) for path in paths if path.exists()]


def _hide_native_title(window: QObject) -> None:
    """The window draws its own centred title under the transparent title bar."""
    if sys.platform != "darwin":
        return
    try:
        import ctypes

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.dylib")
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        get = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        set_long = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(
            address
        )
        view = int(window.winId())
        ns_window = get(view, objc.sel_registerName(b"window")) if view else None
        if ns_window:
            # NSWindowTitleHidden
            set_long(ns_window, objc.sel_registerName(b"setTitleVisibility:"), 1)
    except Exception:  # pragma: no cover - platform specific
        pass


def _native_menu_titles() -> list[str]:
    """Titles in the real NSApp main menu, as AppKit sees it."""
    if sys.platform != "darwin":
        return []
    try:
        import ctypes

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.dylib")
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        send = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        send_long = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(address)
        item_at = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(
            address
        )
        utf8 = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        sel = objc.sel_registerName
        ns_app = send(objc.objc_getClass(b"NSApplication"), sel(b"sharedApplication"))
        menu = send(ns_app, sel(b"mainMenu")) if ns_app else None
        if not menu:
            return []
        titles = []
        for index in range(send_long(menu, sel(b"numberOfItems"))):
            item = item_at(menu, sel(b"itemAtIndex:"), index)
            title = send(item, sel(b"title")) if item else None
            raw = utf8(title, sel(b"UTF8String")) if title else None
            titles.append(raw.decode() if raw else "")
        return titles
    except Exception:  # pragma: no cover - platform specific
        return []


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if raw[:1] == ["--cli"]:
        # Finder Quick Actions, Shortcuts and scripts: no window, no Dock icon.
        from wemute.cli import main as cli_main

        return cli_main(raw[1:])
    arguments = build_parser().parse_args(argv)
    if arguments.image_worker:
        if len(arguments.paths) not in {3, 4}:
            return 2
        from wemute.image_worker import main as image_worker_main

        return image_worker_main(arguments.paths)
    if arguments.ai_worker:
        if len(arguments.paths) != 6:
            return 2
        from wemute.ai_worker import main as ai_worker_main

        return ai_worker_main(arguments.paths)
    if arguments.ai_worker_server:
        from wemute.ai_worker import serve as ai_worker_serve

        return ai_worker_serve()
    if arguments.convert_worker:
        from wemute.convert_worker import main as convert_worker_main

        code = convert_worker_main(arguments.paths)
        sys.stdout.flush()
        sys.stderr.flush()
        # See wemute.convert_worker: skip the interpreter teardown after Vision.
        os._exit(code)
    if arguments.audio_runtime_smoke_test:
        import demucs_mlx  # noqa: F401
        import mlx_audio_io as mac
        import mlx_spectro  # noqa: F401

        mac.supports_soxr()
        return 0
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    QQuickStyle.setStyle("Basic")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = WemuteApplication([sys.argv[0]])
    app.setQuitOnLastWindowClosed(not (arguments.smoke_test or arguments.screenshot))
    app.setApplicationName("Wemute")
    app.setOrganizationName("Wemute")
    app.setApplicationVersion(__version__)
    app_settings = AppSettings(PreferenceStore(DATA_ROOT / "settings.json"))
    if arguments.appearance:
        app_settings.override_appearance(arguments.appearance)
    integrations = Integrations(language=lambda: i18n.language)

    model = QueueModel()
    packages = ModelPackageManager()
    component_controller = ComponentController(ComponentManager())
    controller = JobController(model, packages=packages, components=component_controller)
    ai_model_controller = AIModelController(packages, model.set_enabled_ai_actions)
    app_info_controller = AppInfoController()
    updater_controller = SparkleUpdater()
    if arguments.require_updater and not updater_controller.available:
        updater_controller.shutdown()
        ai_model_controller.shutdown()
        controller.shutdown()
        return 4
    i18n = I18n()
    if arguments.language:
        i18n.override(arguments.language)
    model.set_language(i18n.language)
    i18n.languageChanged.connect(lambda: model.set_language(i18n.language))
    ai_model_controller.set_language(i18n.language)
    i18n.languageChanged.connect(lambda: ai_model_controller.set_language(i18n.language))
    # The default-format grid in 设置 · 转换 shows translated labels.
    i18n.languageChanged.connect(controller.preferencesChanged)

    action_center = ActionCenter(
        controller, app_settings, i18n, ai_models=ai_model_controller, updater=updater_controller
    )
    # Installing or updating ThunderTalk while Wemute runs: pick it up on return.
    integrations.changed.connect(action_center.recheck)
    app.applicationStateChanged.connect(
        lambda state: state == Qt.ApplicationState.ApplicationActive and integrations.refresh()
    )
    native_menu = None
    if sys.platform == "darwin":
        from wemute.menubar import NativeMenuBar

        native_menu = NativeMenuBar(action_center, controller, app_settings, i18n)

    if arguments.demo_dir:
        controller.seed_demo(_demo_descriptors(arguments.demo_dir))
    else:
        if app_settings.restoreSession:
            controller.restore()
        if arguments.paths:
            controller.add_paths(arguments.paths)

    # macOS also delivers launch arguments as FileOpen events; add each path once.
    launch_paths = {str(Path(path).expanduser().resolve()) for path in arguments.paths}

    def open_files(paths: list[str]) -> None:
        fresh = [path for path in paths if str(Path(path).resolve()) not in launch_paths]
        launch_paths.difference_update(str(Path(path).resolve()) for path in paths)
        if fresh:
            controller.add_paths(fresh)

    app.fileOpened.connect(lambda path: open_files([path]))
    if app.pending_file_opens:
        open_files(app.pending_file_opens)
        app.pending_file_opens.clear()

    engine = QQmlApplicationEngine()
    engine.addImageProvider("icons", NativeIconProvider())
    engine.addImageProvider("thumbs", RoundedThumbnailProvider())
    context = engine.rootContext()
    context.setContextProperty("queueModel", model)
    context.setContextProperty("jobController", controller)
    context.setContextProperty("aiModelController", ai_model_controller)
    context.setContextProperty("componentController", component_controller)
    context.setContextProperty("appInfoController", app_info_controller)
    context.setContextProperty("updaterController", updater_controller)
    context.setContextProperty("i18n", i18n)
    context.setContextProperty("appSettings", app_settings)
    context.setContextProperty("integrations", integrations)
    context.setContextProperty("actionCenter", action_center)
    context.setContextProperty("nativeMenus", native_menu is not None)
    engine.load(QUrl.fromLocalFile(str(QML_ROOT / "Main.qml")))
    if not engine.rootObjects():
        controller.shutdown()
        return 2

    root = engine.rootObjects()[0]
    _hide_native_title(root)
    settings_window = root.findChild(QObject, "settingsWindow")
    if settings_window is not None:
        settings_window.visibleChanged.connect(
            lambda: settings_window.property("visible") and _hide_native_title(settings_window)
        )
    if arguments.show_image_options:
        popup = root.findChild(QObject, "imageOptionsPopup")
        if popup:
            QTimer.singleShot(900, popup.open)

    settings_page = arguments.show_settings
    if arguments.show_ai_tools or arguments.show_components:
        settings_page = "components"
    elif arguments.show_about:
        settings_page = "about"
    if settings_page:
        QTimer.singleShot(
            900, lambda: QMetaObject.invokeMethod(root, "openSettings", Q_ARG("QVariant", settings_page))
        )
    if arguments.show_palette is not None:
        QTimer.singleShot(
            900,
            lambda: QMetaObject.invokeMethod(
                root, "openPalette", Q_ARG("QVariant", arguments.show_palette)
            ),
        )
    if arguments.show_tools_menu:
        QTimer.singleShot(900, lambda: QMetaObject.invokeMethod(root, "openToolsMenu"))
    if arguments.show_shortcuts:
        QTimer.singleShot(900, lambda: QMetaObject.invokeMethod(root, "openShortcuts"))
    if arguments.qa_install_model:
        # Press 「获取」 in Settings › Components for this model, report, quit.
        def report(package_id: str, error: str) -> None:
            print(json.dumps({"model": package_id, "ok": not error, "error": error}), flush=True)
            QTimer.singleShot(200, QCoreApplication.quit)

        ai_model_controller._installFinished.connect(report)
        QTimer.singleShot(800, lambda: ai_model_controller.installPackage(arguments.qa_install_model))
    if arguments.qa_action == "start":
        QTimer.singleShot(arguments.qa_action_delay, controller.startAll)
    elif arguments.qa_action == "clear":
        QTimer.singleShot(arguments.qa_action_delay, controller.clearWithUndo)
    if arguments.show_erase_editor:
        image_job = next(
            (job for job in model.jobs if job.source.kind.value == "image"), None
        )
        if image_job:
            QTimer.singleShot(
                900,
                lambda: controller.eraseMaskRequested.emit(
                    image_job.id,
                    QUrl.fromLocalFile(image_job.source.path).toString(),
                    False,
                ),
            )

    def capture_and_maybe_quit() -> None:
        if arguments.smoke_test and native_menu is not None:
            titles = _native_menu_titles()
            if arguments.dump_menu:
                print("menu bar:", " · ".join(titles), flush=True)
            # The application menu plus 文件 编辑 显示 工具 窗口 帮助.
            if len(titles) < 7:
                print(f"native menu bar missing: {titles}", file=sys.stderr, flush=True)
                QCoreApplication.exit(5)
                return
        if arguments.screenshot:
            arguments.screenshot.parent.mkdir(parents=True, exist_ok=True)
            target = root
            if settings_page and settings_window is not None and settings_window.property("visible"):
                target = settings_window
            image = target.grabWindow()
            if not image.save(str(arguments.screenshot)):
                QCoreApplication.exit(3)
                return
        if arguments.screenshot or arguments.smoke_test:
            if settings_window is not None:
                settings_window.setProperty("visible", False)
            root.setProperty("visible", False)
            root.deleteLater()
            QTimer.singleShot(60, QCoreApplication.quit)

    if arguments.show_menu:
        def find_menu(item: QObject) -> QObject | None:
            name = f"formatMenu-{arguments.show_menu}"
            children = list(item.children())
            if hasattr(item, "childItems"):
                children += item.childItems()
            for child in children:
                if child.objectName() == name:
                    return child
                if found := find_menu(child):
                    return found
            return None

        def open_menu(attempts: int = 12) -> None:
            menu = find_menu(root.property("contentItem") or root)
            if menu:
                QMetaObject.invokeMethod(menu, "open")
            elif attempts:
                QTimer.singleShot(250, lambda: open_menu(attempts - 1))
                return
            # Startup can outlast the timers; capture once the menu has faded in.
            if arguments.screenshot or arguments.smoke_test:
                QTimer.singleShot(700, capture_and_maybe_quit)

        QTimer.singleShot(max(1200, arguments.screenshot_delay - 700), open_menu)
    elif arguments.smoke_test or arguments.screenshot:
        QTimer.singleShot(
            arguments.screenshot_delay if arguments.screenshot else 300, capture_and_maybe_quit
        )

    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(ai_model_controller.shutdown)
    app.aboutToQuit.connect(updater_controller.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
