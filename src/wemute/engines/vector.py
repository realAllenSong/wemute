from __future__ import annotations

from pathlib import Path

from wemute.engines.common import Reporter
from wemute.engines.qt import ensure_gui

MIN_RASTER_EDGE = 1024
MAX_RASTER_EDGE = 8192


def raster_size(width: float, height: float) -> tuple[int, int]:
    """Twice the declared size, at least 1024 px on the long edge (icons stay useful)."""
    width, height = max(1.0, width), max(1.0, height)
    long_edge = max(width, height)
    target = min(MAX_RASTER_EDGE, max(MIN_RASTER_EDGE, long_edge * 2))
    scale = target / long_edge
    return max(1, round(width * scale)), max(1, round(height * scale))


def convert(source: Path, output: Path, extension: str, reporter: Reporter) -> None:
    ensure_gui()
    from PySide6.QtCore import QRectF, QSizeF, Qt
    from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
    from PySide6.QtCore import QMarginsF
    from PySide6.QtSvg import QSvgRenderer

    reporter.stage("stage_rendering")
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise reporter.error("bad_svg")
    view = renderer.viewBoxF()
    declared = renderer.defaultSize()
    width = declared.width() if declared.width() > 0 else view.width()
    height = declared.height() if declared.height() > 0 else view.height()
    if width <= 0 or height <= 0:
        width, height = 512.0, 512.0
    renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
    if extension == ".png":
        pixel_width, pixel_height = raster_size(width, height)
        image = QImage(pixel_width, pixel_height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, pixel_width, pixel_height))
        painter.end()
        if not image.save(str(output), "PNG"):
            raise reporter.error("bad_svg")
    else:
        # CSS pixels are 0.75 pt; the page is exactly the drawing.
        page = QPageSize(QSizeF(width * 0.75, height * 0.75), QPageSize.Unit.Point, "", QPageSize.SizeMatchPolicy.ExactMatch)
        writer = QPdfWriter(str(output))
        writer.setPageLayout(QPageLayout(page, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)))
        writer.setResolution(72)
        writer.setTitle(source.stem)
        painter = QPainter(writer)
        renderer.render(painter, QRectF(0, 0, writer.width(), writer.height()))
        painter.end()
        del writer
    reporter.progress(1.0)
