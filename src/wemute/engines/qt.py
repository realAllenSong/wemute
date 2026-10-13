from __future__ import annotations

import os

_APP = None


def ensure_gui() -> None:
    """Qt painting (SVG, rich text, PDF) needs a GUI application; use no windows."""
    global _APP
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QGuiApplication

    existing = QCoreApplication.instance()
    if isinstance(existing, QGuiApplication):
        return
    if existing is not None:
        raise RuntimeError("Qt painting needs a GUI application, not QCoreApplication")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _APP = QGuiApplication(["wemute-convert"])
