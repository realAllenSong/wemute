from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from wemute.paths import ASSET_ROOT


class NativeIconProvider(QQuickImageProvider):
    ICON_IDS = (
        "arrow-right",
        "check",
        "error",
        "file",
        "folder",
        "add",
        "menu",
        "cancel",
        "reveal",
        "image",
        "music",
        "film",
        "clock",
    )

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)
        self._images = {
            icon_id: QImage(str(ASSET_ROOT / "icons" / f"{icon_id}.png"))
            for icon_id in self.ICON_IDS
        }

    def requestImage(  # noqa: N802 - Qt API
        self, icon_id: str, size: QSize, requested_size: QSize
    ) -> QImage:
        pixel_size = requested_size if requested_size.isValid() else QSize(32, 32)
        source = self._images.get(icon_id, self._images["file"])
        image = source.scaled(
            pixel_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image
