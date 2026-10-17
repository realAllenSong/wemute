"""Turns the erase editor's brush strokes into a full-resolution mask image."""
from __future__ import annotations

from PIL import Image, ImageDraw


def draw_erase_mask(strokes: list, size: tuple[int, int]) -> Image.Image:
    """White where the user painted, black elsewhere, at the photo's own size.

    Each stroke is ``{"width": brush diameter, "points": [{"x", "y"}, …]}`` in
    image pixels, with round caps and joins like the editor's preview.
    """
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for stroke in strokes:
        width = max(1.0, float(stroke["width"]))
        radius = width / 2
        points = [(float(point["x"]), float(point["y"])) for point in stroke["points"]]
        if len(points) > 1:
            draw.line(points, fill=255, width=max(1, round(width)))
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    return mask
