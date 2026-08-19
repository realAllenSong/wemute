from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QFileOpenEvent, QPalette
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from wemute.app_info import AppInfoController
from wemute.controller import JobController
from wemute.ai_packages_qt import AIModelController
from wemute.i18n import I18n
from wemute.icon_provider import NativeIconProvider
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
    parser.add_argument("--show-image-options", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-ai-tools", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-erase-editor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-about", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--require-updater", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--image-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ai-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ai-worker-server", action="store_true", help=argparse.SUPPRESS)
    return parser


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#16191C"))
    palette.setColor(QPalette.WindowText, QColor("#F1F2F3"))
    palette.setColor(QPalette.Base, QColor("#1D2125"))
    palette.setColor(QPalette.AlternateBase, QColor("#22272C"))
    palette.setColor(QPalette.Text, QColor("#F1F2F3"))
    palette.setColor(QPalette.Button, QColor("#1D2125"))
    palette.setColor(QPalette.ButtonText, QColor("#F1F2F3"))
    palette.setColor(QPalette.Highlight, QColor("#287BFF"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    return palette


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
    app.setPalette(_dark_palette())

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

    if arguments.demo_dir:
        controller.seed_demo(_demo_descriptors(arguments.demo_dir))
    else:
        controller.restore()
        if arguments.paths:
            controller.add_paths(arguments.paths)

    app.fileOpened.connect(lambda path: controller.add_paths([path]))
    if app.pending_file_opens:
        controller.add_paths(app.pending_file_opens)
        app.pending_file_opens.clear()

    engine = QQmlApplicationEngine()
    engine.addImageProvider("icons", NativeIconProvider())
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
    if arguments.show_image_options:
        popup = root.findChild(QObject, "imageOptionsPopup")
        if popup:
            QTimer.singleShot(350, popup.open)
    if arguments.show_ai_tools:
        popup = root.findChild(QObject, "aiToolsPopup")
        if popup:
            QTimer.singleShot(350, popup.open)
    if arguments.show_erase_editor:
        image_job = next(
            (job for job in model.jobs if job.source.kind.value == "image"), None
        )
        if image_job:
            QTimer.singleShot(
                350,
                lambda: controller.eraseMaskRequested.emit(
                    image_job.id,
                    QUrl.fromLocalFile(image_job.source.path).toString(),
                    False,
                ),
            )
    if arguments.show_about:
        popup = root.findChild(QObject, "aboutPopup")
        if popup:
            QTimer.singleShot(350, popup.open)

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
        QTimer.singleShot(2200 if arguments.screenshot else 300, capture_and_maybe_quit)

    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(ai_model_controller.shutdown)
    app.aboutToQuit.connect(updater_controller.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
