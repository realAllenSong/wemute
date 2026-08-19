from __future__ import annotations

from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication


ICONS = {
    "arrow-right": ("fa6s.arrow-right", "#9EA3AA"),
    "check": ("fa6.circle-check", "#287BFF"),
    "error": ("fa6.circle-xmark", "#FF6B6B"),
    "file": ("fa6.file", "#9EA3AA"),
    "folder": ("fa6.folder", "#9EA3AA"),
    "add": ("fa6s.plus", "#9EA3AA"),
    "menu": ("fa6s.ellipsis", "#A5ABB2"),
    "cancel": ("fa6s.xmark", "#F1F2F3"),
    "reveal": ("fa6.folder-open", "#9EA3AA"),
    "image": ("fa6.image", "#D9DDE1"),
    "music": ("fa6s.music", "#D9DDE1"),
    "film": ("fa6s.film", "#D9DDE1"),
    "clock": ("fa6.clock", "#9EA3AA"),
}


def main() -> None:
    app = QApplication([])
    root = Path(__file__).resolve().parents[1] / "src" / "wemute" / "assets" / "icons"
    root.mkdir(parents=True, exist_ok=True)
    for name, (icon_name, color) in ICONS.items():
        pixmap = qta.icon(icon_name, color=color).pixmap(QSize(128, 128))
        if not pixmap.save(str(root / f"{name}.png"), "PNG"):
            raise RuntimeError(f"Failed to write {name}.png")
    app.quit()


if __name__ == "__main__":
    main()
