from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QFileOpenEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from wemute.app_info import AppInfoController
from wemute.controller import JobController
from wemute.ai_packages_qt import AIModelController
from wemute.i18n import I18n
from wemute.icon_provider import NativeIconProvider, RoundedThumbnailProvider
from wemute.paths import QML_ROOT
from wemute.probe import probe_file
from wemute.queue_model import QueueModel
from wemute.model_packages import ModelPackageManager
from wemute.updater import SparkleUpdater
from wemute import __version__


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
    parser.add_argument("--show-settings", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--appearance", choices=["light", "dark"], help=argparse.SUPPRESS)
    parser.add_argument("--language", choices=["en", "zh"], help=argparse.SUPPRESS)
    parser.add_argument("--require-updater", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--image-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ai-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ai-worker-server", action="store_true", help=argparse.SUPPRESS)
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


def main(argv: list[str] | None = None) -> int:
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
    if arguments.appearance:
        app.styleHints().setColorScheme(
            Qt.ColorScheme.Light if arguments.appearance == "light" else Qt.ColorScheme.Dark
        )


    model = QueueModel()
    packages = ModelPackageManager()
    controller = JobController(model, packages=packages)
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

    if arguments.demo_dir:
        controller.seed_demo(_demo_descriptors(arguments.demo_dir))
    else:
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
    context.setContextProperty("appInfoController", app_info_controller)
    context.setContextProperty("updaterController", updater_controller)
    context.setContextProperty("i18n", i18n)
    engine.load(QUrl.fromLocalFile(str(QML_ROOT / "Main.qml")))
    if not engine.rootObjects():
        controller.shutdown()
        return 2

    root = engine.rootObjects()[0]
    _hide_native_title(root)
    if arguments.show_image_options:
        popup = root.findChild(QObject, "imageOptionsPopup")
        if popup:
            QTimer.singleShot(900, popup.open)
    settings_panel = root.findChild(QObject, "settingsPanel")
    if arguments.show_ai_tools and settings_panel:
        QTimer.singleShot(900, lambda: (settings_panel.setProperty("tab", "ai"), settings_panel.open()))
    if arguments.show_settings and settings_panel:
        QTimer.singleShot(900, settings_panel.open)
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
    if arguments.show_about and settings_panel:
        QTimer.singleShot(900, lambda: (settings_panel.setProperty("tab", "about"), settings_panel.open()))

    def capture_and_maybe_quit() -> None:
        if arguments.screenshot:
            arguments.screenshot.parent.mkdir(parents=True, exist_ok=True)
            image = root.grabWindow()
            if not image.save(str(arguments.screenshot)):
                QCoreApplication.exit(3)
                return
        if arguments.screenshot or arguments.smoke_test:
            root.setProperty("visible", False)
            root.deleteLater()
            QTimer.singleShot(60, QCoreApplication.quit)

    if arguments.smoke_test or arguments.screenshot:
        QTimer.singleShot(
            arguments.screenshot_delay if arguments.screenshot else 300, capture_and_maybe_quit
        )

    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(ai_model_controller.shutdown)
    app.aboutToQuit.connect(updater_controller.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
