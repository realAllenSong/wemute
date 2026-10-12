from __future__ import annotations

from urllib.parse import unquote

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QImage, QPainter, QPainterPath
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

# Lucide-style stroke icons on a 24 px grid (ISC-licensed shapes). Requested as
# ``image://icons/<name>`` or ``image://icons/<name>/<rrggbb>`` to tint them.
ICON_PATHS: dict[str, str] = {
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "circle-x": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "ellipsis": (
        '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'
        '<circle cx="5" cy="12" r="1"/>'
    ),
    "folder": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9'
        'A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
    ),
    "image": (
        '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/>'
        '<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>'
    ),
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "film": (
        '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/>'
        '<path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/>'
        '<path d="M17 7.5h4"/><path d="M17 16.5h4"/>'
    ),
    "file": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
    ),
    "upload": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/>'
        '<path d="M12 3v12"/>'
    ),
    "download": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>'
        '<path d="M12 15V3"/>'
    ),
    "convert": (
        '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/>'
        '<path d="M4 17h16"/>'
    ),
    "sparkles": (
        '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936'
        'A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937'
        'l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135'
        'a.5.5 0 0 1-.963 0z"/>'
    ),
    "settings": (
        '<path d="M21 4h-7"/><path d="M10 4H3"/><path d="M21 12h-9"/><path d="M8 12H3"/>'
        '<path d="M21 20h-5"/><path d="M12 20H3"/><path d="M14 2v4"/><path d="M8 10v4"/>'
        '<path d="M16 18v4"/>'
    ),
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "trash": (
        '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>'
        '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>'
    ),
    "retry": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "lock": (
        '<rect width="18" height="11" x="3" y="11" rx="2"/>'
        '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
    ),
    "gear": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0'
        'l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51'
        'a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08'
        'a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18'
        'a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39'
        'a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09'
        'a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25'
        'a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>'
    ),
    # Filled with the tint colour; "{color}" is substituted at render time.
    "play": (
        '<path fill="{color}" d="M6 4.5a1.5 1.5 0 0 1 2.26-1.3l11 7a1.5 1.5 0 0 1 0 2.6'
        'l-11 7A1.5 1.5 0 0 1 6 18.5z"/>'
    ),
    "audio-lines": (
        '<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/>'
        '<path d="M18 5v13"/><path d="M22 10v3"/>'
    ),
    "alert": '<path d="M12 7v6"/><path d="M12 17.5h.01"/>',
    "folder-open": (
        '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6'
        'a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9'
        'l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>'
    ),
}

# Legacy ids used before the paper redesign.
ALIASES = {
    "error": "circle-x",
    "menu": "ellipsis",
    "add": "plus",
    "cancel": "x",
    "reveal": "folder",
}

DEFAULT_COLOR = "55534E"


def svg_for(name: str, color: str = DEFAULT_COLOR, stroke: float = 1.75) -> bytes:
    body = ICON_PATHS.get(ALIASES.get(name, name), ICON_PATHS["file"])
    body = body.replace("{color}", f"#{color}")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="#{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


class RoundedThumbnailProvider(QQuickImageProvider):
    """``image://thumbs/<radius>/<url-encoded file url>``: cropped to fill, rounded."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)

    def requestImage(  # noqa: N802 - Qt API
        self, image_id: str, size: QSize, requested_size: QSize
    ) -> QImage:
        radius_text, _, encoded = image_id.partition("/")
        location = unquote(encoded)
        path = QUrl(location).toLocalFile() if location.startswith("file:") else location
        logical = requested_size if requested_size.isValid() else QSize(106, 104)
        target = logical * 2
        try:
            radius = float(radius_text) * 2
        except ValueError:
            radius = 0.0
        image = QImage(target, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        source = QImage(path)
        if not source.isNull():
            scaled = source.scaled(
                target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (scaled.width() - target.width()) // 2
            y = (scaled.height() - target.height()) // 2
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0, 0, target.width(), target.height()), radius, radius)
            painter.setClipPath(clip)
            painter.drawImage(0, 0, scaled, x, y, target.width(), target.height())
            painter.end()
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


class NativeIconProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)

    def requestImage(  # noqa: N802 - Qt API
        self, icon_id: str, size: QSize, requested_size: QSize
    ) -> QImage:
        # ``<name>/<rrggbb>/<stroke>``; colour and stroke width are optional.
        name, _, rest = icon_id.partition("/")
        color, _, stroke_text = rest.partition("/")
        color = color.lstrip("#") if len(color.lstrip("#")) == 6 else DEFAULT_COLOR
        try:
            stroke = min(4.0, max(0.5, float(stroke_text))) if stroke_text else 1.75
        except ValueError:
            stroke = 1.75
        logical = requested_size if requested_size.isValid() else QSize(24, 24)
        # Render at 2x so icons stay crisp on Retina displays.
        image = QImage(logical * 2, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        renderer = QSvgRenderer(QByteArray(svg_for(name, color, stroke)))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter, QRectF(0, 0, image.width(), image.height()))
        painter.end()
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image
