"""Photo tools on Apple Vision and Core Image: smart crop, face blur, ID photo
backgrounds, QR/barcode reading, straightening, enhancement, and picking out
blurry and duplicate shots. Every output is full resolution, upright, and keeps
the source colour profile."""

from __future__ import annotations

import csv
import io
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from wemute.engines.common import Reporter
from wemute.engines.vision_io import (
    Photo,
    ci_filter,
    ci_image,
    flatten,
    load_photo,
    normalized_rect,
    perform,
    pil_to_cgimage,
    pixel_buffer_array,
    render_ci,
    resize_mask,
    save_photo,
)

Box = tuple[float, float, float, float]


def _analysis_copy(image: Image.Image, longest: int | None = None) -> Image.Image:
    """An RGB copy for Vision; optionally smaller, since Vision downsamples anyway."""
    rgb = flatten(image)
    if longest and max(rgb.size) > longest:
        rgb = rgb.copy()
        rgb.thumbnail((longest, longest), Image.Resampling.BILINEAR)
    return rgb


def _save_like_source(image: Image.Image, output: Path, photo: Photo, extension: str) -> None:
    save_photo(image, output, photo, extension=extension, quality=93)


# ── faces ────────────────────────────────────────────────────────────────


def detect_faces(image: Image.Image) -> list[Box]:
    import Vision

    request = Vision.VNDetectFaceRectanglesRequest.alloc().init()
    perform(pil_to_cgimage(_analysis_copy(image)), [request])
    width, height = image.size
    return [
        normalized_rect(observation.boundingBox(), width, height)
        for observation in request.results() or []
    ]


def _face_ellipse(box: Box, width: int, height: int) -> Box:
    """Vision boxes hug brows to chin; the ellipse also covers hair, ears and jaw."""
    x0, y0, x1, y1 = box
    face_width, face_height = x1 - x0, y1 - y0
    centre_x = (x0 + x1) / 2
    centre_y = (y0 + y1) / 2 - face_height * 0.1
    half_width = face_width * 0.72
    half_height = face_height * 0.86
    return (
        max(0.0, centre_x - half_width),
        max(0.0, centre_y - half_height),
        min(float(width), centre_x + half_width),
        min(float(height), centre_y + half_height),
    )


# Blocks across a face: few enough that eyes and mouth no longer read as a face.
PIXELATE_BLOCKS = 8


def hide_faces(image: Image.Image, faces: list[Box], style: str = "blur", blocks: int = PIXELATE_BLOCKS) -> Image.Image:
    """Blur or pixelate every face so it cannot be recognised; edges are feathered."""
    result = image.copy()
    width, height = image.size
    for box in faces:
        ellipse = _face_ellipse(box, width, height)
        size = max(ellipse[2] - ellipse[0], ellipse[3] - ellipse[1])
        feather = max(2.0, size * 0.06)
        pad = int(feather * 3)
        left = max(0, int(ellipse[0]) - pad)
        top = max(0, int(ellipse[1]) - pad)
        right = min(width, int(math.ceil(ellipse[2])) + pad)
        bottom = min(height, int(math.ceil(ellipse[3])) + pad)
        if right - left < 2 or bottom - top < 2:
            continue
        region = result.crop((left, top, right, bottom))
        region_size = region.size
        if style == "pixelate":
            block = max(4, round(size / blocks))
            small = (max(1, region_size[0] // block), max(1, region_size[1] // block))
            hidden = region.resize(small, Image.Resampling.BOX).resize(region_size, Image.Resampling.NEAREST)
        else:
            # Shrinking first removes all detail; the blur afterwards hides the blocks.
            small = (max(1, round(region_size[0] / max(1.0, size / 9))), max(1, round(region_size[1] / max(1.0, size / 9))))
            hidden = region.resize(small, Image.Resampling.BOX).resize(region_size, Image.Resampling.BICUBIC)
            hidden = hidden.filter(ImageFilter.GaussianBlur(max(2.0, size / 14)))
        mask = Image.new("L", region_size, 0)
        ImageDraw.Draw(mask).ellipse(
            (ellipse[0] - left, ellipse[1] - top, ellipse[2] - left, ellipse[3] - top), fill=255
        )
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
        if result.mode == "RGBA":
            hidden.putalpha(region.getchannel("A"))
        region.paste(hidden, (0, 0), mask)
        result.paste(region, (left, top))
    return result


# ── smart crop ───────────────────────────────────────────────────────────

RATIOS = {"1:1": (1, 1), "4:5": (4, 5), "16:9": (16, 9), "9:16": (9, 16)}


def _saliency(image: Image.Image) -> tuple[np.ndarray, list[Box]]:
    """Where the eye goes, as a small heat map (row 0 at the top, sums to 1), and
    the faces with room for hair above them, in pixels."""
    import Vision

    copy = _analysis_copy(image, 1600)
    cg_image = pil_to_cgimage(copy)
    attention = Vision.VNGenerateAttentionBasedSaliencyImageRequest.alloc().init()
    objectness = Vision.VNGenerateObjectnessBasedSaliencyImageRequest.alloc().init()
    perform(cg_image, [attention, objectness])
    observation = (attention.results() or [None])[0]
    heat = pixel_buffer_array(observation.pixelBuffer()) if observation is not None else None
    things = (objectness.results() or [None])[0]
    if heat is None or float(heat.max()) < 0.05:
        heat = pixel_buffer_array(things.pixelBuffer()) if things is not None else None
    width, height = image.size
    grid_width = 160
    grid_height = max(1, round(grid_width * height / width))
    if heat is None or float(heat.max()) <= 0:
        heat_map = np.zeros((grid_height, grid_width), np.float32)
    else:
        heat_map = np.clip(resize_mask(heat, (grid_width, grid_height)), 0, None)
        heat_map /= max(float(heat_map.sum()), 1e-9)
    scale = width / copy.width
    faces = []
    for box in detect_faces(copy):
        x0, y0, x1, y1 = _face_ellipse(box, copy.width, copy.height)
        outer = (x0 * scale, max(0.0, y0 - 0.12 * (y1 - y0)) * scale, x1 * scale, y1 * scale)
        faces.append((outer, tuple(value * scale for value in box)))
    if not faces and things is not None:
        # Attention maps lean towards the centre; a distinct object (a boat, a
        # product) should not be sliced in half when it fits.
        for item in things.salientObjects() or []:
            x0, y0, x1, y1 = normalized_rect(item.boundingBox(), width, height)
            if (x1 - x0) * (y1 - y0) < 0.5 * width * height:
                faces.append(((x0, y0, x1, y1), (x0, y0, x1, y1)))
    return heat_map, faces


def crop_window(
    heat: np.ndarray,
    size: tuple[int, int],
    ratio: tuple[int, int],
    faces: list[tuple[Box, Box]] | None = None,
) -> Box:
    """The largest crop of ``ratio`` that keeps the most attention and never
    slices through a face when it can avoid it, in pixels."""
    width, height = size
    target = ratio[0] / ratio[1]
    if width / height > target:
        crop_width, crop_height = height * target, float(height)
    else:
        crop_width, crop_height = float(width), width / target
    horizontal = crop_width < width - 0.5
    if not horizontal and crop_height > height - 0.5:
        return 0.0, 0.0, float(width), float(height)
    length, span = (width, crop_width) if horizontal else (height, crop_height)
    profile = heat.sum(axis=0 if horizontal else 1).astype(np.float64)
    cells = len(profile)
    cumulative = np.concatenate([[0.0], np.cumsum(profile)])
    intervals = []
    for outer, core in faces or []:
        axis = (0, 2) if horizontal else (1, 3)
        # With hair and chin the face may not fit; then brows to chin must.
        box = outer if outer[axis[1]] - outer[axis[0]] <= span else core
        intervals.append((box[axis[0]], box[axis[1]]))
    face_weight = 1.0 / max(1, len(intervals))
    total = float(profile.sum())
    if intervals:
        centroid = sum(low + high for low, high in intervals) / (2 * len(intervals))
    elif total > 0:
        centroid = float((profile * (np.arange(cells) + 0.5)).sum() / total) / cells * length
    else:
        centroid = length / 2

    def score(start: float) -> float:
        end = start + span
        kept = cumulative[int(round(end / length * cells))] - cumulative[int(round(start / length * cells))]
        value = float(kept)
        for low, high in intervals:
            inside = max(0.0, min(end, high) - max(start, low)) / max(high - low, 1.0)
            if high - low > span:
                value += face_weight * 2.0 * inside
            else:
                # A whole face is worth keeping; half a face is worse than none.
                value += face_weight * (2.0 if inside > 0.999 else (-1.5 * inside if inside > 0 else 0.0))
        return value

    steps = max(2, min(400, int(length - span) + 1))
    starts = np.linspace(0.0, length - span, steps)
    scores = np.array([score(float(start)) for start in starts])
    best = float(scores.max())
    candidates = starts[scores >= best - 0.01 * max(abs(best), 1e-6)]
    start = float(min(candidates, key=lambda value: abs(value + span / 2 - centroid)))
    if horizontal:
        return start, 0.0, start + crop_width, float(height)
    return 0.0, start, float(width), start + crop_height


def smart_crop(image: Image.Image, ratio: str) -> Image.Image:
    heat, faces = _saliency(image)
    window = crop_window(heat, image.size, RATIOS[ratio], faces)
    return image.crop(tuple(int(round(value)) for value in window))


# ── ID photo background ──────────────────────────────────────────────────

ID_COLORS = {"white": (255, 255, 255), "blue": (67, 142, 219), "red": (217, 0, 21)}


def person_mask(image: Image.Image) -> np.ndarray:
    import Vision

    request = Vision.VNGeneratePersonSegmentationRequest.alloc().initWithCompletionHandler_(None)
    request.setQualityLevel_(Vision.VNGeneratePersonSegmentationRequestQualityLevelAccurate)
    perform(pil_to_cgimage(flatten(image)), [request])
    observation = (request.results() or [None])[0]
    if observation is None:
        return np.zeros((image.height, image.width), np.float32)
    mask = pixel_buffer_array(observation.pixelBuffer())
    return np.clip(resize_mask(mask, image.size), 0.0, 1.0)


def replace_background(image: Image.Image, mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    from wemute.mattes import decontaminate_edges, finish_alpha, guided_refine

    rgb = np.asarray(flatten(image))
    radius = max(2, round(max(image.size) / 320))
    alpha = finish_alpha(guided_refine(rgb, mask, radius))
    colors = decontaminate_edges(rgb, alpha, radius).astype(np.float32)
    background = np.array(color, np.float32)
    composed = colors * alpha[..., None] + background * (1.0 - alpha[..., None])
    return Image.fromarray(np.clip(np.rint(composed), 0, 255).astype(np.uint8), "RGB")


# ── QR codes and barcodes ────────────────────────────────────────────────


@dataclass
class Code:
    symbology: str
    payload: str


def read_codes(image: Image.Image) -> list[Code]:
    import Vision

    request = Vision.VNDetectBarcodesRequest.alloc().init()
    perform(pil_to_cgimage(_analysis_copy(image)), [request])
    codes: list[Code] = []
    seen: set[tuple[str, str]] = set()
    for observation in request.results() or []:
        payload = observation.payloadStringValue()
        if not payload:
            continue
        symbology = str(observation.symbology()).removeprefix("VNBarcodeSymbology")
        key = (symbology, str(payload))
        if key not in seen:
            seen.add(key)
            codes.append(Code(symbology, str(payload)))
    return codes


# ── straighten ───────────────────────────────────────────────────────────

LEVEL_TOLERANCE = 0.5


def horizon_angle(image: Image.Image) -> float | None:
    """Degrees to rotate (counter-clockwise) so the horizon is level."""
    import Vision

    request = Vision.VNDetectHorizonRequest.alloc().init()
    perform(pil_to_cgimage(_analysis_copy(image, 2048)), [request])
    observation = (request.results() or [None])[0]
    if observation is None:
        return None
    return math.degrees(float(observation.angle()))


def _inscribed_size(width: float, height: float, angle: float) -> tuple[float, float]:
    """Largest axis-aligned rectangle inside a ``width``×``height`` frame rotated by ``angle``."""
    angle = abs(math.radians(angle)) % math.pi
    if angle > math.pi / 2:
        angle = math.pi - angle
    sin, cos = math.sin(angle), math.cos(angle)
    long_side, short_side = max(width, height), min(width, height)
    if short_side <= 2 * sin * cos * long_side or abs(sin - cos) < 1e-10:
        half = 0.5 * short_side
        if width >= height:
            return half / sin, half / cos
        return half / cos, half / sin
    cos_2a = cos * cos - sin * sin
    return (width * cos - height * sin) / cos_2a, (height * cos - width * sin) / cos_2a


def straighten(image: Image.Image, angle: float) -> Image.Image:
    rotated = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
    width, height = image.size
    crop_width, crop_height = _inscribed_size(width, height, angle)
    left = (width - crop_width) / 2
    top = (height - crop_height) / 2
    box = (
        int(math.ceil(left)),
        int(math.ceil(top)),
        int(math.floor(left + crop_width)),
        int(math.floor(top + crop_height)),
    )
    return rotated.crop(box)


# ── enhance ──────────────────────────────────────────────────────────────

HIGH_ISO = 1600


def enhance(image: Image.Image, iso: int | None = None) -> Image.Image:
    """Apple's own auto adjustments (no red-eye pass), plus noise reduction for high ISO."""
    import Quartz

    rgb = flatten(image)
    source = ci_image(rgb)
    extent = source.extent()
    result = source
    if iso and iso >= HIGH_ISO:
        # Before brightening, so the lift does not amplify the grain.
        level = 0.04 if iso < 3200 else 0.06 if iso < 6400 else 0.08
        result = ci_filter(
            "CINoiseReduction", inputImage=result, inputNoiseLevel=level, inputSharpness=0.5
        ).outputImage()
    filters = source.autoAdjustmentFiltersWithOptions_({Quartz.kCIImageAutoAdjustRedEye: False}) or []
    for item in filters:
        item.setValue_forKey_(result, Quartz.kCIInputImageKey)
        result = item.outputImage()
    enhanced = render_ci(result.imageByCroppingToRect_(extent), extent)
    if image.mode == "RGBA":
        enhanced = enhanced.convert("RGBA")
        enhanced.putalpha(image.getchannel("A"))
    return enhanced


# ── blurry and duplicate photos ──────────────────────────────────────────

DUPLICATE_DISTANCE = 0.35
BLURRY_SHARPNESS = 45.0


def sharpness(image: Image.Image) -> float:
    """Detail in the sharpest parts of the frame (90th percentile of tile
    Laplacian variance at 1024 px), so a sharp subject on a soft background counts."""
    gray = image.convert("L")
    gray.thumbnail((1024, 1024), Image.Resampling.BILINEAR)
    values = np.asarray(gray, dtype=np.float32)
    if min(values.shape) < 16:
        return 0.0
    laplacian = (
        4 * values[1:-1, 1:-1] - values[:-2, 1:-1] - values[2:, 1:-1] - values[1:-1, :-2] - values[1:-1, 2:]
    )
    rows, cols = laplacian.shape
    tile_rows, tile_cols = max(1, rows // 8), max(1, cols // 8)
    tiles = [
        float(laplacian[r * tile_rows : (r + 1) * tile_rows, c * tile_cols : (c + 1) * tile_cols].var())
        for r in range(8)
        for c in range(8)
    ]
    return float(np.percentile(tiles, 90))


def aesthetics_score(cg_image) -> float | None:  # noqa: ANN001
    """Vision's overall aesthetics score (macOS 15+), −1 to 1; None when unavailable."""
    import Vision

    if not hasattr(Vision, "VNCalculateImageAestheticsScoresRequest"):
        return None
    try:
        request = Vision.VNCalculateImageAestheticsScoresRequest.alloc().initWithCompletionHandler_(None)
        perform(cg_image, [request])
        observation = (request.results() or [None])[0]
        return float(observation.overallScore()) if observation is not None else None
    except Exception:  # noqa: BLE001 - the score only refines the choice
        return None


def feature_print(cg_image) -> np.ndarray:  # noqa: ANN001
    import Vision

    request = Vision.VNGenerateImageFeaturePrintRequest.alloc().init()
    perform(cg_image, [request])
    observation = request.results()[0]
    dtype = np.float32 if int(observation.elementType()) == 1 else np.float64
    vector = np.frombuffer(bytes(observation.data()), dtype=dtype).astype(np.float32)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


@dataclass
class Shot:
    path: Path
    vector: np.ndarray
    sharpness: float
    aesthetics: float | None
    pixels: int

    def quality(self, largest: int) -> float:
        """Which of near-identical shots to keep: the better looking one, unless
        another is clearly larger (a downscaled or cropped copy loses)."""
        base = self.aesthetics if self.aesthetics is not None else 0.0
        resolution = 0.5 * math.log(max(self.pixels, 1) / max(largest, 1))
        return base + resolution + 0.1 * math.tanh(self.sharpness / 400)

    def is_blurry(self) -> bool:
        if self.sharpness < BLURRY_SHARPNESS:
            return True
        return self.aesthetics is not None and self.aesthetics < 0.25 and self.sharpness < 4 * BLURRY_SHARPNESS


def analyse_shot(path: Path, reporter: Reporter) -> Shot:
    photo = load_photo(path, reporter)
    small = _analysis_copy(photo.image, 1024)
    cg_image = pil_to_cgimage(small)
    return Shot(
        path,
        feature_print(cg_image),
        sharpness(photo.image),
        aesthetics_score(cg_image),
        photo.image.width * photo.image.height,
    )


def duplicate_groups(shots: list[Shot]) -> list[list[int]]:
    """Indices of near-identical shots, best first; singletons are left out."""
    parent = list(range(len(shots)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for first in range(len(shots)):
        for second in range(first + 1, len(shots)):
            distance = float(np.linalg.norm(shots[first].vector - shots[second].vector))
            if distance < DUPLICATE_DISTANCE:
                parent[find(second)] = find(first)
    clusters: dict[int, list[int]] = {}
    for index in range(len(shots)):
        clusters.setdefault(find(index), []).append(index)
    groups = []
    for members in clusters.values():
        if len(members) > 1:
            largest = max(shots[index].pixels for index in members)
            groups.append(sorted(members, key=lambda index: -shots[index].quality(largest)))
    return groups


def _copy_into(source: Path, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / source.name
    number = 2
    while target.exists():
        target = folder / f"{source.stem} {number}{source.suffix}"
        number += 1
    shutil.copy2(source, target)
    return target


_TRIAGE_TEXT = {
    "zh": {
        "duplicates": "重复",
        "blurry": "模糊",
        "report": "报告.csv",
        "header": ["文件", "建议", "原因", "原文件", "清晰度", "美学评分"],
        "duplicate_of": "和 {name} 几乎一样，那张更好",
        "blurry_reason": "画面模糊",
        "keep": "保留",
        "review": "建议删除",
    },
    "en": {
        "duplicates": "Duplicates",
        "blurry": "Blurry",
        "report": "Report.csv",
        "header": ["File", "Suggestion", "Reason", "Original", "Sharpness", "Aesthetics"],
        "duplicate_of": "Nearly the same as {name}, which is better",
        "blurry_reason": "Out of focus or shaken",
        "keep": "Keep",
        "review": "Consider deleting",
    },
}


def triage(sources: list[Path], output: Path, reporter: Reporter) -> tuple[int, int]:
    """Copy suggested duplicates and blurry shots into a review folder with a CSV
    report. Originals are never moved or deleted."""
    text = _TRIAGE_TEXT.get(reporter.language, _TRIAGE_TEXT["en"])
    reporter.stage("stage_analyzing")
    shots: list[Shot] = []
    for index, source in enumerate(sources):
        shots.append(analyse_shot(source, reporter))
        reporter.progress(0.85 * (index + 1) / len(sources))
    reporter.stage("stage_comparing")
    duplicates: dict[int, int] = {}
    for members in duplicate_groups(shots):
        for index in members[1:]:
            duplicates[index] = members[0]
    blurry = {index for index, shot in enumerate(shots) if index not in duplicates and shot.is_blurry()}
    reporter.stage("stage_saving")
    output.mkdir(parents=True, exist_ok=True)
    duplicate_folder = output / text["duplicates"]
    blurry_folder = output / text["blurry"]
    duplicate_folder.mkdir(exist_ok=True)
    blurry_folder.mkdir(exist_ok=True)
    rows: list[list[str]] = []
    for index, shot in enumerate(shots):
        reason = ""
        if index in duplicates:
            copied = _copy_into(shot.path, duplicate_folder)
            reason = text["duplicate_of"].format(name=shots[duplicates[index]].path.name)
        elif index in blurry:
            copied = _copy_into(shot.path, blurry_folder)
            reason = text["blurry_reason"]
        else:
            copied = None
        rows.append(
            [
                str(copied.relative_to(output)) if copied else shot.path.name,
                text["review"] if copied else text["keep"],
                reason,
                str(shot.path),
                f"{shot.sharpness:.0f}",
                "" if shot.aesthetics is None else f"{shot.aesthetics:.2f}",
            ]
        )
    rows.sort(key=lambda row: row[1] == text["keep"])
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(text["header"])
    writer.writerows(rows)
    (output / text["report"]).write_text(buffer.getvalue(), encoding="utf-8-sig")
    reporter.progress(1.0)
    return len(duplicates), len(blurry)


# ── jobs ─────────────────────────────────────────────────────────────────


def run_photo_tool(tool: str, source: Path, output: Path, extension: str, options: dict, reporter: Reporter) -> None:
    photo = load_photo(source, reporter)
    reporter.progress(0.12)
    reporter.stage("stage_analyzing")
    image = photo.image
    if tool == "crop":
        result = smart_crop(image, str(options.get("ratio", "1:1")))
    elif tool == "faces":
        faces = detect_faces(image)
        if not faces:
            raise reporter.error("no_faces")
        reporter.progress(0.45)
        result = hide_faces(image, faces, str(options.get("style", "blur")))
    elif tool == "id_photo":
        mask = person_mask(image)
        if float(mask.max()) < 0.5 or float(mask.mean()) < 0.01:
            raise reporter.error("no_person")
        reporter.progress(0.5)
        reporter.stage("stage_enhancing")
        result = replace_background(image, mask, ID_COLORS.get(str(options.get("color")), ID_COLORS["white"]))
    elif tool == "straighten":
        angle = horizon_angle(image)
        if angle is None:
            raise reporter.error("no_horizon")
        if abs(angle) < LEVEL_TOLERANCE:
            raise reporter.error("already_level", angle=f"{abs(angle):.1f}")
        reporter.progress(0.4)
        result = straighten(image, angle)
    elif tool == "enhance":
        reporter.stage("stage_enhancing")
        result = enhance(image, photo.iso)
    else:
        raise ValueError(f"Unknown photo tool: {tool}")
    reporter.progress(0.85)
    reporter.stage("stage_saving")
    _save_like_source(result, output, photo, extension)
    reporter.progress(1.0)


def codes_to_file(sources: list[Path], output: Path, as_csv: bool, reporter: Reporter) -> None:
    reporter.stage("stage_analyzing")
    rows: list[tuple[str, str, str]] = []
    for index, source in enumerate(sources):
        photo = load_photo(source, reporter)
        rows.extend((source.name, code.symbology, code.payload) for code in read_codes(photo.image))
        reporter.progress(0.9 * (index + 1) / len(sources))
    if not rows:
        raise reporter.error("no_codes")
    reporter.stage("stage_saving")
    if as_csv:
        header = ["文件", "类型", "内容"] if reporter.language == "zh" else ["File", "Type", "Content"]
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        writer.writerows(rows)
        output.write_text(buffer.getvalue(), encoding="utf-8-sig")
    else:
        output.write_text("".join(f"{name}\t{kind}\t{payload}\n" for name, kind, payload in rows), encoding="utf-8")
    reporter.progress(1.0)
