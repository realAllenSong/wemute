from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter, ImageOps

from wemute.mattes import (
    decontaminate_edges,
    dilate,
    finish_alpha,
    guided_refine,
)


ort.set_default_logger_severity(3)

ProgressCallback = Callable[[float], None]
EventCallback = Callable[[dict[str, object]], None]

STAGE_LABELS: dict[str, tuple[str, str]] = {
    "prepare": ("Preparing model…", "准备模型…"),
    "prepare-first": ("Preparing model for first use…", "首次准备模型…"),
    "process": ("Processing…", "处理中…"),
    "save": ("Saving…", "保存…"),
}


class WorkerError(RuntimeError):
    """A failure with a stable code the UI can translate."""

    def __init__(self, code: str, english: str, chinese: str) -> None:
        super().__init__(chinese if _language() == "zh" else english)
        self.code = code


def _language() -> str:
    try:
        from PySide6.QtCore import QSettings

        from wemute.i18n import I18n

        return I18n._resolve(str(QSettings("Wemute", "Wemute").value("language", "system")))
    except Exception:
        return "en"


def _progress(value: float) -> None:
    print(f"wemute_progress={max(0.0, min(1.0, value)):.3f}", flush=True)


# ── progress reporting ───────────────────────────────────────────────────


def estimate_fraction(elapsed: float, expected: float) -> float:
    """Share of an un-instrumented step assumed done after ``elapsed`` seconds.

    Reaches 85 % at the expected duration, then keeps creeping toward 98 % so
    an overrun still shows movement. Mirrored by ``_TICKER_AWK``.
    """
    expected = max(0.05, expected)
    if elapsed <= expected:
        return 0.85 * (1.0 - math.exp(-3.0 * elapsed / expected)) / (1.0 - math.exp(-3.0))
    return 0.85 + 0.13 * (1.0 - math.exp(-(elapsed - expected) / (3.0 * expected)))


# Runs outside the interpreter so it keeps ticking while native code holds the
# GIL (ONNX Runtime session creation, Core ML compilation, MLX loading).
_TICKER_AWK = r"""
BEGIN {
  t = 0; last = -1
  while (t < limit) {
    system("sleep " step); t += step
    if (t <= expected) f = 0.85 * (1 - exp(-3 * t / expected)) / (1 - exp(-3))
    else f = 0.85 + 0.13 * (1 - exp(-(t - expected) / (3 * expected)))
    v = start + (stop - start) * f
    if (v - last >= 0.001) { printf "%s%.4f%s\n", prefix, v, suffix; fflush(); last = v }
  }
}
"""


class Reporter:
    """Turns stages, real fractions and time-based estimates into worker events."""

    interval = 0.2

    def __init__(
        self,
        emit: EventCallback,
        ticker_line: tuple[str, str] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._emit = emit
        self._ticker_line = ticker_line
        self._clock = clock
        self._lock = threading.Lock()
        self.value = 0.0
        self.stage_id = ""

    @classmethod
    def wrap(cls, progress: ProgressCallback | "Reporter") -> "Reporter":
        if isinstance(progress, Reporter):
            return progress
        return cls(lambda event: progress(float(event["value"])) if event["type"] == "progress" else None)

    def __call__(self, value: float) -> None:
        self.progress(value)

    def progress(self, value: float) -> None:
        with self._lock:
            value = max(self.value, min(1.0, float(value)))
            if value <= self.value and value < 1.0 and self.value > 0.0:
                return
            self.value = value
        self._emit({"type": "progress", "value": round(value, 4)})

    def stage(self, stage_id: str) -> None:
        english, chinese = STAGE_LABELS[stage_id]
        self.stage_id = stage_id
        self._emit(
            {
                "type": "stage",
                "stage": stage_id,
                "label": chinese if _language() == "zh" else english,
            }
        )

    def span(self, start: float, stop: float) -> ProgressCallback:
        return lambda fraction: self.progress(start + (stop - start) * max(0.0, min(1.0, fraction)))

    @contextmanager
    def estimate(self, start: float, stop: float, expected: float) -> Iterator[None]:
        """Advance smoothly from ``start`` toward ``stop`` while the block runs."""
        self.progress(start)
        began = self._clock()
        ticker = self._start_ticker(start, stop, expected)
        finished = threading.Event()
        thread = None
        if ticker is None:
            def beat() -> None:
                while not finished.wait(self.interval):
                    fraction = estimate_fraction(self._clock() - began, expected)
                    self.progress(start + (stop - start) * fraction)

            thread = threading.Thread(target=beat, name="wemute-heartbeat", daemon=True)
            thread.start()
        try:
            yield
        finally:
            finished.set()
            if thread is not None:
                thread.join()
            if ticker is not None:
                ticker.kill()
                ticker.wait()
                # The ticker may have printed one step ahead of this process.
                elapsed = self._clock() - began + self.interval
                with self._lock:
                    self.value = max(
                        self.value, start + (stop - start) * estimate_fraction(elapsed, expected)
                    )
        self.progress(stop)

    def _start_ticker(self, start: float, stop: float, expected: float) -> subprocess.Popen | None:
        if self._ticker_line is None or not Path("/usr/bin/awk").is_file():
            return None
        prefix, suffix = self._ticker_line
        try:
            sys.stdout.flush()
            return subprocess.Popen(
                [
                    "/usr/bin/awk",
                    "-v", f"start={start}",
                    "-v", f"stop={stop}",
                    "-v", f"expected={max(0.05, expected)}",
                    "-v", f"step={self.interval}",
                    "-v", f"limit={max(60.0, expected * 8)}",
                    "-v", f"prefix={prefix}",
                    "-v", f"suffix={suffix}",
                    _TICKER_AWK,
                ],
                stdin=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={"LC_ALL": "C", "PATH": "/bin:/usr/bin"},
            )
        except OSError:
            return None


# ── ONNX sessions ────────────────────────────────────────────────────────


def _input_size(session: ort.InferenceSession) -> tuple[int, int]:
    shape = session.get_inputs()[0].shape
    height = int(shape[-2]) if isinstance(shape[-2], int) else 320
    width = int(shape[-1]) if isinstance(shape[-1], int) else 320
    return width, height


# LaMa compiles to Core ML for 12–25 s yet runs no faster than on the CPU.
_CPU_ONLY_BACKENDS = {"onnxruntime-lama"}


def _providers(model: Path, backend: str = "") -> list[object]:
    available = ort.get_available_providers()
    providers: list[object] = []
    if "CoreMLExecutionProvider" in available and backend not in _CPU_ONLY_BACKENDS:
        providers.append(
            (
                "CoreMLExecutionProvider",
                {
                    "ModelFormat": "MLProgram",
                    "MLComputeUnits": "ALL",
                    "RequireStaticInputShapes": "1",
                    "ModelCacheDirectory": str(_coreml_cache(model)),
                },
            )
        )
    if "CPUExecutionProvider" in available:
        providers.append("CPUExecutionProvider")
    return providers or available


def _coreml_cache(model: Path) -> Path:
    cache = model.parent / "coreml-cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


class InferenceSessionCache:
    def __init__(self) -> None:
        self._sessions: dict[tuple[Path, str], ort.InferenceSession] = {}
        self._resources: dict[Hashable, object] = {}

    def has_session(self, model: Path, backend: str) -> bool:
        return (model.resolve(), backend) in self._sessions

    def has_resource(self, key: Hashable) -> bool:
        return key in self._resources

    def session(self, model: Path, backend: str) -> ort.InferenceSession:
        key = (model.resolve(), backend)
        session = self._sessions.get(key)
        if session is None:
            providers = _providers(model, backend)
            try:
                session = ort.InferenceSession(str(model), providers=providers)
            except Exception:
                if "CPUExecutionProvider" not in ort.get_available_providers():
                    raise
                session = ort.InferenceSession(
                    str(model), providers=["CPUExecutionProvider"]
                )
            self._sessions[key] = session
        return session

    def resource(self, key: Hashable, factory: Callable[[], object]) -> object:
        resource = self._resources.get(key)
        if resource is None:
            resource = factory()
            self._resources[key] = resource
        return resource


def _prepare_session(
    reporter: Reporter,
    sessions: InferenceSessionCache,
    model: Path,
    backend: str,
    start: float,
    stop: float,
) -> ort.InferenceSession:
    if sessions.has_session(model, backend):
        reporter.progress(stop)
        return sessions.session(model, backend)
    uses_coreml = backend not in _CPU_ONLY_BACKENDS and (
        "CoreMLExecutionProvider" in ort.get_available_providers()
    )
    first_time = uses_coreml and not any(_coreml_cache(model).iterdir())
    reporter.stage("prepare-first" if first_time else "prepare")
    megabytes = model.stat().st_size / 1_000_000 if model.is_file() else 50.0
    expected = (25.0 if first_time else 12.0) if uses_coreml else 0.6 + megabytes * 0.025
    with reporter.estimate(start, stop, expected):
        return sessions.session(model, backend)


# ── image helpers ────────────────────────────────────────────────────────


def _open_upright(source: Path) -> tuple[Image.Image, dict[str, object]]:
    with Image.open(source) as opened:
        info = {"icc_profile": opened.info.get("icc_profile")}
        image = ImageOps.exif_transpose(opened)
        image = image.convert("RGBA" if _has_alpha(image) else "RGB")
    return image, info


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in {"RGBA", "LA", "PA"} or (
        image.mode == "P" and "transparency" in image.info
    )


def _save_png(image: Image.Image, destination: Path, info: dict[str, object]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    options: dict[str, object] = {"compress_level": 6}
    if info.get("icc_profile"):
        options["icc_profile"] = info["icc_profile"]
    image.save(destination, "PNG", **options)


def _megapixels(image: Image.Image) -> float:
    return image.width * image.height / 1_000_000


# ── remove background: Apple Vision ──────────────────────────────────────


def _no_subject() -> WorkerError:
    return WorkerError("no_subject", "No subject found", "没有找到可以抠出的主体")


def vision_foreground_mask(image: Image.Image) -> np.ndarray:
    """Soft foreground mask (float32, 0–1) for every instance, at full resolution."""
    from wemute.vision_mask import foreground_mask

    mask = foreground_mask(image)
    if mask is None:
        raise _no_subject()
    return mask


def remove_background_vision(
    source: Path,
    destination: Path,
    progress: ProgressCallback | Reporter = _progress,
) -> None:
    reporter = Reporter.wrap(progress)
    reporter.stage("process")
    image, info = _open_upright(source)
    reporter.progress(0.08)
    with reporter.estimate(0.08, 0.78, 0.4 + _megapixels(image) * 0.06):
        mask = vision_foreground_mask(image)
    if float(mask.max()) < 0.5:
        raise _no_subject()
    rgba = np.asarray(image.convert("RGBA"))
    alpha = mask
    if image.mode == "RGBA":
        alpha = alpha * (rgba[..., 3].astype(np.float32) / 255.0)
    with reporter.estimate(0.78, 0.86, 0.2 + _megapixels(image) * 0.27):
        radius = max(2, round(max(image.size) / 300))
        alpha = finish_alpha(guided_refine(rgba[..., :3], alpha, radius))
        colors = decontaminate_edges(rgba[..., :3], alpha, radius)
    output = np.dstack([colors, np.rint(alpha * 255.0).astype(np.uint8)])
    reporter.stage("save")
    with reporter.estimate(0.86, 0.99, 0.2 + _megapixels(image) * 0.12):
        _save_png(Image.fromarray(output, mode="RGBA"), destination, info)
    reporter.progress(1.0)


# ── remove background: ONNX fallback (non-macOS) ─────────────────────────


def _prepare_u2net(image: Image.Image, size: tuple[int, int]) -> np.ndarray:
    resized = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    tensor = np.asarray(resized, dtype=np.float32) / 255.0
    mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
    tensor = (tensor - mean) / std
    return np.transpose(tensor, (2, 0, 1))[None, ...]


def _normalise_mask(output: np.ndarray) -> np.ndarray:
    mask = np.squeeze(output).astype(np.float32)
    if mask.ndim == 3:
        mask = mask[0]
    if float(mask.min()) < 0.0 or float(mask.max()) > 1.0:
        mask = 1.0 / (1.0 + np.exp(-np.clip(mask, -30.0, 30.0)))
    low = float(mask.min())
    high = float(mask.max())
    if math.isclose(low, high):
        return np.zeros_like(mask)
    return (mask - low) / (high - low)


def remove_background(
    source: Path,
    destination: Path,
    model: Path,
    backend: str,
    sessions: InferenceSessionCache,
    progress: ProgressCallback | Reporter = _progress,
) -> None:
    reporter = Reporter.wrap(progress)
    image, info = _open_upright(source)
    image = image.convert("RGBA")
    session = _prepare_session(reporter, sessions, model, backend, 0.02, 0.3)
    reporter.stage("process")
    tensor = _prepare_u2net(image, _input_size(session))
    with reporter.estimate(0.3, 0.84, 2.5):
        output = session.run(None, {session.get_inputs()[0].name: tensor})[0]
    mask = _normalise_mask(output)
    if float(mask.max()) < 0.5:
        raise _no_subject()
    alpha = Image.fromarray(np.uint8(np.clip(mask, 0.0, 1.0) * 255), mode="L")
    alpha = alpha.resize(image.size, Image.Resampling.LANCZOS)
    image.putalpha(alpha)
    reporter.stage("save")
    with reporter.estimate(0.86, 0.99, 0.2 + _megapixels(image) * 0.12):
        _save_png(image, destination, info)
    reporter.progress(1.0)


# ── upscale: Real-ESRGAN ─────────────────────────────────────────────────

_PERCENT = re.compile(r"(\d+(?:\.\d+)?)%")


def upscale_image(
    source: Path,
    destination: Path,
    runtime: Path,
    options: dict[str, object],
    progress: ProgressCallback | Reporter = _progress,
) -> None:
    reporter = Reporter.wrap(progress)
    executable = runtime / "realesrgan-ncnn-vulkan"
    models = runtime / "models"
    if not executable.is_file() or not models.is_dir():
        raise FileNotFoundError("The Real-ESRGAN runtime is incomplete. Reinstall the AI package.")
    scale = int(options.get("scale", 2))
    if scale not in {2, 4}:
        raise ValueError("Real-ESRGAN scale must be 2 or 4.")
    style = str(options.get("style", "photo"))
    model_name = (
        "realesrgan-x4plus-anime" if style == "illustration" else "realesrgan-x4plus"
    )
    reporter.stage("prepare")
    reporter.progress(0.02)
    with tempfile.TemporaryDirectory(prefix="wemute-upscale-") as temporary_directory:
        normalized = Path(temporary_directory) / "input.png"
        from wemute.image_worker import convert_image

        convert_image(source, normalized, "PNG")
        destination.parent.mkdir(parents=True, exist_ok=True)
        reporter.progress(0.06)
        process = subprocess.Popen(
            [
                str(executable),
                "-i", str(normalized),
                "-o", str(destination),
                "-s", str(scale),
                "-m", str(models),
                "-n", model_name,
                "-f", "png",
            ],
            cwd=runtime,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        tiles = reporter.span(0.12, 0.97)
        messages = _follow_tiles(process, reporter, tiles)
        returncode = process.wait()
    if returncode != 0:
        message = "\n".join(line for line in messages if not _PERCENT.fullmatch(line)).strip()
        raise RuntimeError(message.splitlines()[-1] if message else "Real-ESRGAN failed.")
    if not destination.is_file():
        raise RuntimeError("Real-ESRGAN did not produce an output image.")
    reporter.progress(1.0)


def _follow_tiles(
    process: subprocess.Popen, reporter: Reporter, tiles: ProgressCallback
) -> list[str]:
    """Map the helper's per-tile percentages onto the progress bar.

    Until the first tile reports (GPU and model start-up) a time estimate keeps
    the bar moving.
    """
    lines: list[str] = []
    first_tile = threading.Event()
    stream = process.stderr
    assert stream is not None

    def read() -> None:
        buffer = b""
        while chunk := stream.read1(256):
            buffer += chunk
            *complete, buffer = re.split(rb"[\r\n]", buffer)
            for raw in complete:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                lines.append(line)
                match = _PERCENT.fullmatch(line)
                if match:
                    if not first_tile.is_set():
                        first_tile.set()
                        reporter.stage("process")
                    tiles(float(match.group(1)) / 100.0)
        if buffer.strip():
            lines.append(buffer.decode("utf-8", errors="replace").strip())

    reader = threading.Thread(target=read, name="wemute-realesrgan", daemon=True)
    reader.start()
    began = time.monotonic()
    while reader.is_alive() and not first_tile.is_set():
        fraction = estimate_fraction(time.monotonic() - began, 1.5)
        reporter.progress(0.06 + 0.06 * fraction)
        reader.join(Reporter.interval)
    reader.join()
    return lines


# ── erase: crop-and-paste LaMa inpainting ────────────────────────────────

LAMA_SIZE = 512
_MERGE_GAP = 48


def load_erase_mask(mask_path: Path, size: tuple[int, int]) -> np.ndarray:
    with Image.open(mask_path) as opened_mask:
        mask_rgba = opened_mask.convert("RGBA")
        alpha = mask_rgba.getchannel("A")
        has_transparency = "A" in opened_mask.getbands() and alpha.getextrema() != (255, 255)
        mask = alpha if has_transparency else opened_mask.convert("L")
        mask.load()
    if mask.size != size:
        mask = mask.resize(size, Image.Resampling.BILINEAR)
    return np.asarray(mask) >= 64


def _components(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Bounding boxes (x0, y0, x1, y1) of mask regions; nearby strokes merge."""
    height, width = mask.shape
    cell = max(1, math.ceil(max(height, width) / 512))
    rows = math.ceil(height / cell)
    cols = math.ceil(width / cell)
    padded = np.zeros((rows * cell, cols * cell), dtype=bool)
    padded[:height, :width] = mask
    coarse = padded.reshape(rows, cell, cols, cell).any(axis=(1, 3))
    joined = dilate(coarse, max(1, math.ceil(_MERGE_GAP / 2 / cell)))
    labels = np.zeros(coarse.shape, dtype=np.int32)
    boxes: list[tuple[int, int, int, int]] = []
    for start_row, start_col in zip(*np.nonzero(coarse)):
        if labels[start_row, start_col]:
            continue
        label = len(boxes) + 1
        stack = [(int(start_row), int(start_col))]
        labels[start_row, start_col] = label
        members: list[tuple[int, int]] = []
        while stack:
            row, col = stack.pop()
            members.append((row, col))
            for next_row, next_col in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if (
                    0 <= next_row < rows
                    and 0 <= next_col < cols
                    and joined[next_row, next_col]
                    and not labels[next_row, next_col]
                ):
                    labels[next_row, next_col] = label
                    stack.append((next_row, next_col))
        member_rows = [row for row, col in members if coarse[row, col]]
        member_cols = [col for row, col in members if coarse[row, col]]
        row0, row1 = min(member_rows), max(member_rows) + 1
        col0, col1 = min(member_cols), max(member_cols) + 1
        top, left = row0 * cell, col0 * cell
        region = mask[top : row1 * cell, left : col1 * cell]
        own = (labels[row0:row1, col0:col1] == label).repeat(cell, 0).repeat(cell, 1)
        ys, xs = np.nonzero(region & own[: region.shape[0], : region.shape[1]])
        boxes.append(
            (left + int(xs.min()), top + int(ys.min()), left + int(xs.max()) + 1, top + int(ys.max()) + 1)
        )
    return boxes


Box = tuple[int, int, int, int]


# LaMa darkens a hole that fills much of its 512 px window (a flat grey hole
# covering 75 % of the window comes back ~18 % darker). Three times the hole's
# size keeps it small in the window: on a sail at sunset and a painting on a
# wall this removed the ghost and the dark smear that twice the size left.
CONTEXT_FACTOR = 3


def _context_side(box: Box) -> int:
    return max(LAMA_SIZE, CONTEXT_FACTOR * max(box[2] - box[0], box[3] - box[1]))


def _edge_padding(mask: np.ndarray) -> int:
    """How far to mirror the photo outward when a hole touches its border, so
    the hole has context on every side instead of the frame edge."""
    height, width = mask.shape
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if not len(rows):
        return 0
    margin = 8
    touches = rows[0] < margin or cols[0] < margin or rows[-1] >= height - margin or cols[-1] >= width - margin
    if not touches:
        return 0
    size = max(rows[-1] - rows[0], cols[-1] - cols[0]) + 1
    return int(min(size * 0.6, min(height, width) - 1))


def context_crop(box: Box, width: int, height: int) -> Box:
    """Square crop around ``box``: at least twice its size and 512 px, kept inside the image."""
    x0, y0, x1, y1 = box
    side = _context_side(box)
    crop_width = min(side, width)
    crop_height = min(side, height)
    left = int(round((x0 + x1) / 2 - crop_width / 2))
    top = int(round((y0 + y1) / 2 - crop_height / 2))
    left = max(0, min(width - crop_width, left))
    top = max(0, min(height - crop_height, top))
    return left, top, left + crop_width, top + crop_height


def plan_regions(mask: np.ndarray) -> list[Box]:
    """Boxes to inpaint one at a time: nearby strokes share a pass, long thin
    strokes (text, wires) are cut into pieces so each is inpainted near 1:1."""
    regions: list[Box] = []
    for box in _merge_boxes(_components(mask)):
        regions.extend(_split_long(box, mask))
    return regions


def _split_long(box: Box, mask: np.ndarray) -> list[Box]:
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    long_side, short_side = max(width, height), min(width, height)
    piece = max(short_side, LAMA_SIZE // CONTEXT_FACTOR)
    if CONTEXT_FACTOR * long_side <= LAMA_SIZE * 1.25 or long_side <= piece * 1.25:
        return [box]
    count = math.ceil(long_side / piece)
    pieces: list[Box] = []
    for index in range(count):
        start = round(index * long_side / count)
        stop = round((index + 1) * long_side / count)
        if width >= height:
            part = (x0 + start, y0, x0 + stop, y1)
        else:
            part = (x0, y0 + start, x1, y0 + stop)
        ys, xs = np.nonzero(mask[part[1] : part[3], part[0] : part[2]])
        if len(xs):
            pieces.append(
                (part[0] + int(xs.min()), part[1] + int(ys.min()), part[0] + int(xs.max()) + 1, part[1] + int(ys.max()) + 1)
            )
    return pieces or [box]


def _merge_boxes(boxes: list[Box]) -> list[Box]:
    side = _context_side
    merged = list(boxes)
    changed = True
    while changed:
        changed = False
        for first in range(len(merged)):
            for second in range(first + 1, len(merged)):
                a, b = merged[first], merged[second]
                union = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                # One pass is better when it costs little resolution.
                if side(union) <= 1.25 * max(side(a), side(b)):
                    merged[first] = union
                    del merged[second]
                    changed = True
                    break
            if changed:
                break
    return sorted(merged, key=lambda box: (box[1], box[0]))


def _lama_tensors(crop: np.ndarray, hole: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int]]:
    height, width = hole.shape
    square = max(height, width)
    pad_y = (square - height) // 2
    pad_x = (square - width) // 2
    padding = ((pad_y, square - height - pad_y), (pad_x, square - width - pad_x))
    image = crop
    hole_square = hole
    if height != width:
        image = np.pad(crop, (*padding, (0, 0)), mode="symmetric")
        hole_square = np.pad(hole, padding)
    resized = Image.fromarray(image).resize((LAMA_SIZE, LAMA_SIZE), Image.Resampling.LANCZOS)
    image_tensor = np.asarray(resized, dtype=np.float32)[..., ::-1] / 255.0
    image_tensor = np.transpose(image_tensor, (2, 0, 1))[None, ...].copy()
    # Any coverage of a 512 px cell marks it as a hole, so nothing leaks through.
    hole_small = Image.fromarray(np.uint8(hole_square) * 255).resize(
        (LAMA_SIZE, LAMA_SIZE), Image.Resampling.BOX
    )
    mask_tensor = (np.asarray(hole_small) > 0).astype(np.float32)[None, None, ...]
    return image_tensor, mask_tensor, (square, pad_y, pad_x)


def _lama_output(output: np.ndarray, geometry: tuple[int, int, int], height: int, width: int) -> np.ndarray:
    square, pad_y, pad_x = geometry
    result = np.transpose(output[0], (1, 2, 0))[..., ::-1]
    result = Image.fromarray(np.uint8(np.clip(np.rint(result), 0, 255)), mode="RGB")
    result = result.resize((square, square), Image.Resampling.LANCZOS)
    return np.asarray(result)[pad_y : pad_y + height, pad_x : pad_x + width]


def erase_regions(
    rgb: np.ndarray,
    mask: np.ndarray,
    inpaint: Callable[[np.ndarray, np.ndarray], np.ndarray],
    regions: list[Box] | None = None,
) -> np.ndarray:
    """Inpaint each region in a context crop and paste back only its mask.

    ``inpaint(image_tensor, mask_tensor)`` returns LaMa's 512×512 output. Every
    pixel outside the dilated, feathered mask is copied from ``rgb`` unchanged.
    """
    height, width = mask.shape
    result = rgb.copy()
    for box in regions if regions is not None else plan_regions(mask):
        left, top, right, bottom = context_crop(box, width, height)
        crop_mask = mask[top:bottom, left:right]
        own = np.zeros_like(crop_mask)
        own[box[1] - top : box[3] - top, box[0] - left : box[2] - left] = True
        own &= crop_mask
        scale = max(right - left, bottom - top) / LAMA_SIZE
        grow = max(3, math.ceil(2.0 * scale))
        feather = max(2, math.ceil(1.5 * scale))
        reach = grow + 3 * feather + 1
        # Every painted pixel in the crop is a hole, so unfinished neighbouring
        # strokes are never copied as context; only this region is pasted.
        hole = dilate(crop_mask, reach)
        paste = dilate(own, reach)
        crop = result[top:bottom, left:right]
        image_tensor, mask_tensor, geometry = _lama_tensors(crop, hole)
        generated = _lama_output(inpaint(image_tensor, mask_tensor), geometry, bottom - top, right - left)
        alpha = np.asarray(
            Image.fromarray(np.uint8(dilate(own, grow)) * 255).filter(ImageFilter.GaussianBlur(feather)),
            dtype=np.float32,
        ) / 255.0
        alpha = np.where(own, 1.0, alpha)
        alpha = np.where(paste, alpha, 0.0)[..., None]
        blended = np.rint(crop * (1.0 - alpha) + generated * alpha).astype(np.uint8)
        result[top:bottom, left:right] = np.where(alpha > 0.0, blended, crop)
    return result


def erase_object(
    source: Path,
    destination: Path,
    model: Path,
    backend: str,
    options: dict[str, object],
    sessions: InferenceSessionCache,
    progress: ProgressCallback | Reporter = _progress,
) -> None:
    reporter = Reporter.wrap(progress)
    mask_value = options.get("mask_path")
    if not mask_value:
        raise ValueError("Draw a mask before starting object erase.")
    mask_path = Path(str(mask_value))
    if not mask_path.is_file():
        raise FileNotFoundError("The erase mask is missing. Draw it again.")
    image, info = _open_upright(source)
    mask = load_erase_mask(mask_path, image.size)
    if not mask.any():
        raise WorkerError("empty_mask", "Paint over what you want to remove first.", "请先涂抹想要移除的区域。")
    reporter.progress(0.03)
    session = _prepare_session(reporter, sessions, model, backend, 0.03, 0.25)
    reporter.stage("process")
    inputs = [item.name for item in session.get_inputs()]
    rgb = np.asarray(image.convert("RGB"))
    regions = plan_regions(mask)
    share = (0.9 - 0.25) / max(1, len(regions))
    state = {"done": 0}

    def inpaint(image_tensor: np.ndarray, mask_tensor: np.ndarray) -> np.ndarray:
        start = 0.25 + state["done"] * share
        with reporter.estimate(start, start + share, 1.8):
            output = session.run(None, {inputs[0]: image_tensor, inputs[1]: mask_tensor})[0]
        state["done"] += 1
        return output

    pad = _edge_padding(mask)
    if pad:
        # The mirrored copy of the hole is a hole too, so nothing painted leaks back.
        padded = erase_regions(
            np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)), mode="reflect"),
            np.pad(mask, pad, mode="reflect"),
            inpaint,
        )
        erased = padded[pad:-pad, pad:-pad]
    else:
        erased = erase_regions(rgb, mask, inpaint, regions)
    reporter.stage("save")
    composed = Image.fromarray(erased, mode="RGB")
    if image.mode == "RGBA":
        composed.putalpha(image.getchannel("A"))
    with reporter.estimate(0.9, 0.99, 0.2 + _megapixels(image) * 0.12):
        _save_png(composed, destination, info)
    reporter.progress(1.0)


# ── separate vocals: MLX Demucs ──────────────────────────────────────────


def _load_mlx_separator(runtime: Path) -> object:
    from demucs_mlx.mlx_convert import load_mlx_model_from_safetensors

    return load_mlx_model_from_safetensors(
        "htdemucs",
        cache_dir=str(runtime),
        verbose=False,
    )


def _apply_mlx_separator(model: object, source: Path) -> tuple[np.ndarray, np.ndarray, int]:
    import mlx.core as mx
    import mlx_audio_io as mac
    from demucs_mlx.apply_mlx import apply_model

    sample_rate = int(getattr(model, "samplerate", 44_100))
    audio, loaded_rate = mac.load(str(source), sr=sample_rate, dtype="float32")
    sample_rate = int(loaded_rate)
    audio_array = np.asarray(audio, dtype=np.float32)
    if audio_array.ndim == 1:
        audio_array = audio_array[:, None]
    expected_channels = int(getattr(model, "audio_channels", 2))
    if audio_array.shape[1] == 1 and expected_channels == 2:
        audio_array = np.repeat(audio_array, 2, axis=1)
    elif audio_array.shape[1] != expected_channels:
        audio_array = audio_array[:, :expected_channels]
    mix = mx.array(np.ascontiguousarray(audio_array.T[None, ...]))
    estimates = apply_model(
        model,
        mix,
        shifts=0,
        split=True,
        overlap=0.25,
        progress=False,
        batch_size=1,
        seed=0,
    )
    mx.eval(estimates)
    stems = np.asarray(estimates[0], dtype=np.float32)
    sources = list(getattr(model, "sources", ("drums", "bass", "other", "vocals")))
    try:
        vocal_index = sources.index("vocals")
    except ValueError as exc:
        raise RuntimeError("The separation model does not provide a vocals stem.") from exc
    vocals = stems[vocal_index]
    instrumental = np.sum(np.delete(stems, vocal_index, axis=0), axis=0)
    return vocals, instrumental, sample_rate


def _save_audio_stem(audio: np.ndarray, destination: Path, sample_rate: int) -> None:
    from demucs_mlx.audio import save_audio

    # demucs-mlx currently maps 24/32-bit requests to float WAV.
    # PCM16 has the widest playback compatibility across Finder, browsers,
    # editors, and the bundled FFmpeg probe path.
    save_audio(audio, destination, sample_rate, clip="clamp", bits_per_sample=16)


def _expected_separation_seconds(source: Path) -> float:
    try:
        megabytes = source.stat().st_size / 1_000_000
    except OSError:
        megabytes = 5.0
    # Compressed sources hold more audio per byte than WAV.
    per_megabyte = 0.35 if source.suffix.lower() in {".wav", ".aif", ".aiff"} else 3.0
    return max(4.0, megabytes * per_megabyte)


def separate_vocals(
    source: Path,
    vocals_destination: Path,
    runtime: Path,
    options: dict[str, object],
    sessions: InferenceSessionCache,
    progress: ProgressCallback | Reporter = _progress,
) -> None:
    reporter = Reporter.wrap(progress)
    instrumental_value = options.get("instrumental_destination")
    if not instrumental_value:
        raise ValueError("The instrumental output destination is missing.")
    instrumental_destination = Path(str(instrumental_value))
    weights = runtime / "htdemucs.safetensors"
    config = runtime / "htdemucs_config.json"
    if not weights.is_file() or not config.is_file():
        raise FileNotFoundError("The vocal separation package is incomplete. Reinstall it.")
    key = ("mlx-htdemucs", runtime.resolve())
    reporter.progress(0.02)
    if sessions.has_resource(key):
        model = sessions.resource(key, lambda: _load_mlx_separator(runtime))
    else:
        reporter.stage("prepare")
        with reporter.estimate(0.02, 0.12, 3.0):
            model = sessions.resource(key, lambda: _load_mlx_separator(runtime))
    reporter.stage("process")
    with reporter.estimate(0.12, 0.88, _expected_separation_seconds(source)):
        vocals, instrumental, sample_rate = _apply_mlx_separator(model, source)
    reporter.stage("save")
    vocals_destination.parent.mkdir(parents=True, exist_ok=True)
    instrumental_destination.parent.mkdir(parents=True, exist_ok=True)
    _save_audio_stem(vocals, vocals_destination, sample_rate)
    reporter.progress(0.94)
    _save_audio_stem(instrumental, instrumental_destination, sample_rate)
    reporter.progress(1.0)


# ── dispatch and protocol ────────────────────────────────────────────────


def run(
    operation: str,
    source: Path,
    destination: Path,
    model: Path,
    backend: str,
    options: dict[str, object] | None = None,
    sessions: InferenceSessionCache | None = None,
    progress: ProgressCallback | Reporter = _progress,
) -> None:
    options = options or {}
    sessions = sessions or InferenceSessionCache()
    if operation == "remove-background" and backend == "apple-vision":
        remove_background_vision(source, destination, progress)
        return
    if operation == "remove-background" and backend in {
        "onnxruntime-u2net",
        "onnxruntime-birefnet",
    }:
        remove_background(source, destination, model, backend, sessions, progress)
        return
    if operation == "upscale" and backend == "realesrgan-ncnn-vulkan":
        upscale_image(source, destination, model, options, progress)
        return
    if operation == "erase-object" and backend == "onnxruntime-lama":
        erase_object(source, destination, model, backend, options, sessions, progress)
        return
    if operation == "separate-vocals" and backend == "mlx-htdemucs":
        separate_vocals(source, destination, model, options, sessions, progress)
        return
    raise ValueError(f"Unsupported AI worker operation/backend: {operation}/{backend}")


_output_lock = threading.Lock()


def _event(output: TextIO, payload: dict[str, object]) -> None:
    line = f"wemute_event={json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    with _output_lock:
        print(line, file=output, flush=True)


def _ticker_line(output: TextIO, job_id: str) -> tuple[str, str] | None:
    """Prefix/suffix for progress lines the out-of-process ticker may print."""
    try:
        if output.fileno() != sys.stdout.fileno():
            return None
    except (AttributeError, OSError, ValueError):
        return None
    prefix = "wemute_event=" + json.dumps(
        {"job_id": job_id, "type": "progress"}, separators=(",", ":")
    )[:-1] + ',"value":'
    return prefix, "}"


def serve(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
    sessions = InferenceSessionCache()
    for raw_line in input_stream:
        if not raw_line.strip():
            continue
        job_id = ""
        try:
            request = json.loads(raw_line)
            if not isinstance(request, dict):
                raise ValueError("AI worker request must be an object.")
            job_id = str(request["job_id"])
            reporter = Reporter(
                lambda payload, job_id=job_id: _event(output_stream, {"job_id": job_id, **payload}),
                _ticker_line(output_stream, job_id),
            )
            run(
                str(request["operation"]),
                Path(str(request["source"])),
                Path(str(request["destination"])),
                Path(str(request["model"])),
                str(request["backend"]),
                dict(request.get("options", {})),
                sessions,
                reporter,
            )
            _event(output_stream, {"job_id": job_id, "type": "result", "ok": True})
        except Exception as exc:
            payload: dict[str, object] = {
                "job_id": job_id,
                "type": "result",
                "ok": False,
                "error": str(exc),
            }
            if isinstance(exc, WorkerError):
                payload["code"] = exc.code
            _event(output_stream, payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if arguments == ["--serve"]:
        return serve()
    if len(arguments) != 6:
        return 2
    operation, source, destination, model, backend, raw_options = arguments
    reporter = Reporter(
        lambda payload: _progress(float(payload["value"]))
        if payload["type"] == "progress"
        else print(f"wemute_stage={payload['stage']}", flush=True),
        ("wemute_progress=", ""),
    )
    try:
        run(
            operation,
            Path(source),
            Path(destination),
            Path(model),
            backend,
            json.loads(raw_options),
            InferenceSessionCache(),
            reporter,
        )
    except Exception as exc:  # Worker failures must never take down the UI process.
        print(str(exc), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
