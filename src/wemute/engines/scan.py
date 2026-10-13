"""Document scanning: find the page in a photo, flatten it, and clean it up."""

from __future__ import annotations

import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from wemute.engines.common import ConversionError, Reporter
from wemute.engines.vision_io import (
    Photo,
    ci_filter,
    ci_image,
    flatten,
    load_photo,
    perform,
    pil_to_cgimage,
    render_ci,
    save_photo,
)

Corners = tuple[tuple[float, float], ...]  # top-left, top-right, bottom-right, bottom-left (px, origin top-left)

# Below this share of the frame a detected "page" is more likely a label or a screen.
_MIN_AREA = 0.06


def _quad_area(points: Corners) -> float:
    total = 0.0
    for index, (x0, y0) in enumerate(points):
        x1, y1 = points[(index + 1) % len(points)]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2


def _observation_corners(observation, width: int, height: int) -> Corners:  # noqa: ANN001
    def pixel(point) -> tuple[float, float]:  # noqa: ANN001
        return float(point.x) * width, (1 - float(point.y)) * height

    return (
        pixel(observation.topLeft()),
        pixel(observation.topRight()),
        pixel(observation.bottomRight()),
        pixel(observation.bottomLeft()),
    )


def find_document(image: Image.Image) -> Corners | None:
    """Page corners in pixels, or None when no page edges are visible."""
    import Vision

    width, height = image.size
    cg_image = pil_to_cgimage(flatten(image))
    candidates: list[Corners] = []
    if hasattr(Vision, "VNDetectDocumentSegmentationRequest"):
        request = Vision.VNDetectDocumentSegmentationRequest.alloc().init()
        perform(cg_image, [request])
        for observation in request.results() or []:
            if float(observation.confidence()) >= 0.5:
                candidates.append(_observation_corners(observation, width, height))
    if not candidates:
        request = Vision.VNDetectRectanglesRequest.alloc().init()
        request.setMaximumObservations_(4)
        request.setMinimumSize_(0.25)
        request.setMinimumAspectRatio_(0.25)
        request.setMaximumAspectRatio_(1.0)
        request.setQuadratureTolerance_(30.0)
        request.setMinimumConfidence_(0.6)
        perform(cg_image, [request])
        candidates = [
            _observation_corners(observation, width, height)
            for observation in request.results() or []
        ]
    candidates = [item for item in candidates if _quad_area(item) >= _MIN_AREA * width * height]
    if not candidates:
        return None
    return max(candidates, key=_quad_area)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _edge_ratio(corners: Corners) -> float:
    top_left, top_right, bottom_right, bottom_left = corners
    page_width = max(_distance(top_left, top_right), _distance(bottom_left, bottom_right))
    page_height = max(_distance(top_left, bottom_left), _distance(top_right, bottom_right))
    return page_height / page_width if page_width > 0 else 1.0


def page_ratio(corners: Corners, size: tuple[int, int], focal_35mm: float | None = None) -> float:
    """Height / width of the real page, undoing the camera's foreshortening.

    Zhang & He, "Whiteboard scanning and image enhancement" (2007): with the
    principal point at the image centre, the page's corners fix the focal
    length and the true aspect ratio. A curled receipt breaks the flat-page
    assumption and yields an implausible focal length; the longest-edge
    estimate is used then.
    """
    width, height = size
    long_side = max(width, height)
    tl, tr, br, bl = (np.array([x - width / 2, y - height / 2, 1.0]) for x, y in corners)
    try:
        k2 = np.dot(np.cross(tl, br), bl) / np.dot(np.cross(tr, br), bl)
        k3 = np.dot(np.cross(tl, br), tr) / np.dot(np.cross(bl, br), tr)
    except (FloatingPointError, ZeroDivisionError):
        return _edge_ratio(corners)
    n2, n3 = k2 * tr - tl, k3 * bl - tl
    if not (np.isfinite(n2).all() and np.isfinite(n3).all()):
        return _edge_ratio(corners)
    if abs(n2[2]) < 1e-9 or abs(n3[2]) < 1e-9:
        # Opposite edges parallel in the photo: no foreshortening to undo.
        return float(math.hypot(n3[0], n3[1]) / max(math.hypot(n2[0], n2[1]), 1e-9))
    if focal_35mm:
        focal_squared = (focal_35mm / 36.0 * long_side) ** 2
    else:
        focal_squared = -(n2[0] * n3[0] + n2[1] * n3[1]) / (n2[2] * n3[2])
        if not 0.5 * long_side <= math.sqrt(max(focal_squared, 0.0)) <= 1.6 * long_side:
            return _edge_ratio(corners)
    across = (n2[0] ** 2 + n2[1] ** 2) / focal_squared + n2[2] ** 2
    down = (n3[0] ** 2 + n3[1] ** 2) / focal_squared + n3[2] ** 2
    if across <= 0 or down <= 0:
        return _edge_ratio(corners)
    return float(math.sqrt(down / across))


def _focal_35mm(photo: Photo) -> float | None:
    if not photo.exif:
        return None
    try:
        exif = Image.Exif()
        exif.load(photo.exif)
        value = exif.get_ifd(0x8769).get(0xA405)
        return float(value) if value and float(value) > 0 else None
    except Exception:  # noqa: BLE001 - optional hint
        return None


def flatten_page(image: Image.Image, corners: Corners, focal_35mm: float | None = None) -> Image.Image:
    """Perspective-correct the page at full resolution (Core Image)."""
    import Quartz

    _width, height = image.size
    top_left, top_right, bottom_right, bottom_left = corners

    def vector(point: tuple[float, float]):  # noqa: ANN202 - Core Image uses a bottom-left origin
        return Quartz.CIVector.vectorWithX_Y_(point[0], height - point[1])

    corrected = ci_filter(
        "CIPerspectiveCorrection",
        inputImage=ci_image(flatten(image)),
        inputTopLeft=vector(top_left),
        inputTopRight=vector(top_right),
        inputBottomRight=vector(bottom_right),
        inputBottomLeft=vector(bottom_left),
    ).outputImage()
    flat = render_ci(corrected)
    # Core Image keeps the longer of each opposite edge pair; match the page's
    # real proportions instead.
    target_height = round(flat.width * page_ratio(corners, image.size, focal_35mm))
    if target_height > 0 and abs(target_height - flat.height) > 2:
        flat = flat.resize((flat.width, target_height), Image.Resampling.LANCZOS)
    # Detected corners sit on the paper's edge; a hairline inset drops the table.
    inset_x, inset_y = round(flat.width * 0.006), round(flat.height * 0.006)
    return flat.crop((inset_x, inset_y, flat.width - inset_x, flat.height - inset_y))


def _paper_background(gray: np.ndarray) -> np.ndarray:
    """Local paper brightness: text and lines removed by a max filter, then smoothed."""
    height, width = gray.shape
    factor = max(1, round(max(width, height) / 900))
    small = Image.fromarray(gray).resize(
        (max(1, width // factor), max(1, height // factor)), Image.Resampling.BOX
    )
    reach = max(3, round(min(small.size) / 60)) | 1
    small = small.filter(ImageFilter.MaxFilter(reach)).filter(ImageFilter.MaxFilter(reach))
    small = small.filter(ImageFilter.GaussianBlur(reach * 1.5))
    return np.asarray(small.resize((width, height), Image.Resampling.BILINEAR), dtype=np.float32)


def enhance_document(image: Image.Image, mode: str = "color") -> Image.Image:
    """Even out lighting and turn the paper white; ``mode`` is "color" or "bw"."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    gray = (rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)).clip(0, 255).astype(np.uint8)
    background = np.maximum(_paper_background(gray), 40.0)
    if mode == "bw":
        level = (gray.astype(np.float32) / background).clip(0, 1.2)
        # Ink stays solid, the paper goes clean white; a soft ramp keeps edges smooth.
        ink, paper = 0.55, 0.86
        value = ((level - ink) / (paper - ink)).clip(0, 1) ** 1.6
        return Image.fromarray((value * 255 + 0.5).astype(np.uint8), "L")
    # Each channel against its own paper level: a warm lamp or yellowed paper
    # turns white while coloured ink, stamps and highlights keep their hue.
    channels = []
    for channel in range(3):
        plane = rgb[..., channel].clip(0, 255).astype(np.uint8)
        channels.append(rgb[..., channel] / np.maximum(_paper_background(plane), 40.0))
    normalised = np.dstack(channels).clip(0, 1.2)
    black, white = 0.12, 0.9
    value = ((normalised - black) / (white - black)).clip(0, 1)
    # Lift faint colour that the whitening washed out.
    mean = value.mean(axis=2, keepdims=True)
    value = (mean + (value - mean) * 1.2).clip(0, 1)
    return Image.fromarray((value ** 1.15 * 255 + 0.5).astype(np.uint8), "RGB")


def scan_image(photo: Photo, mode: str, reporter: Reporter, *, require_page: bool = True) -> Image.Image:
    reporter.stage("stage_finding_edges")
    corners = find_document(photo.image)
    if corners is None:
        if require_page:
            raise reporter.error("no_document")
        page = flatten(photo.image)
    else:
        page = flatten_page(photo.image, corners, _focal_35mm(photo))
    reporter.stage("stage_enhancing")
    return enhance_document(page, mode)


def scan_to_image(source: Path, output: Path, mode: str, reporter: Reporter) -> None:
    photo = load_photo(source, reporter)
    reporter.progress(0.1)
    page = scan_image(photo, mode, reporter)
    reporter.progress(0.8)
    reporter.stage("stage_saving")
    # The page is a new picture: no camera orientation or lens EXIF applies to it.
    save_photo(page, output, Photo(page, photo.icc if mode != "bw" else None), quality=90)
    reporter.progress(1.0)


def _page_stream(page: Image.Image) -> tuple:
    buffer = io.BytesIO()
    page.save(buffer, "JPEG", quality=82 if page.mode == "L" else 85, optimize=True)
    colorspace = "/DeviceGray" if page.mode == "L" else "/DeviceRGB"
    return buffer.getvalue(), "/DCTDecode", page.width, page.height, colorspace


def scan_to_pdf(sources: list[Path], output: Path, mode: str, reporter: Reporter) -> None:
    """One flattened, cleaned, searchable page per photo."""
    import pikepdf

    from wemute.engines import ocr

    pdf = pikepdf.Pdf.new()
    font = ocr.ocr_font(pdf)
    group = len(sources) > 1
    for index, source in enumerate(sources):
        base = index / len(sources)
        span = 1 / len(sources)
        photo = load_photo(source, reporter)
        try:
            page = scan_image(photo, mode, reporter, require_page=not group)
        except ConversionError:
            raise
        reporter.progress(base + span * 0.5)
        reporter.stage("stage_recognizing")
        lines = ocr.recognize(page.convert("RGB"))
        ocr.add_image_page(pdf, font, _page_stream(page), lines)
        reporter.progress(base + span * 0.95)
    reporter.stage("stage_saving")
    pdf.save(output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    reporter.progress(1.0)
