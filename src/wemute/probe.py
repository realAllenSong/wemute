from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageOps

from wemute.domain import FileDescriptor, MediaKind
from wemute.native_images import HEIC_SUFFIXES, decode_heic, heic_dimensions
from wemute.paths import THUMBNAIL_ROOT, resolve_engine

IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
    ".avif",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
}
AUDIO_SUFFIXES = {
    ".mp3",
    ".wav",
    ".flac",
    ".m4a",
    ".aac",
    ".aiff",
    ".aif",
    ".ogg",
    ".opus",
}
VIDEO_SUFFIXES = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
    ".avi",
}
DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"}


def media_kind_for(path: Path) -> MediaKind:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return MediaKind.IMAGE
    if suffix in AUDIO_SUFFIXES:
        return MediaKind.AUDIO
    if suffix in VIDEO_SUFFIXES:
        return MediaKind.VIDEO
    if suffix in DOCUMENT_SUFFIXES:
        return MediaKind.DOCUMENT
    return MediaKind.OTHER


def expand_paths(paths: Iterable[str | Path]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_file():
            files.append(path.resolve())
        elif path.is_dir():
            try:
                files.extend(
                    child.resolve()
                    for child in sorted(path.rglob("*"))
                    if child.is_file() and not child.name.startswith(".")
                )
            except OSError:
                continue
    # Preserve order while de-duplicating.
    return list(dict.fromkeys(files))


def _ffprobe(path: Path) -> dict[str, Any]:
    executable = resolve_engine("ffprobe")
    if not executable:
        return {}
    command = [
        str(executable),
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,width,height,sample_rate,channels,duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, timeout=12, check=True)
        return json.loads(result.stdout or b"{}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def _thumbnail_key(path: Path) -> str:
    try:
        marker = f"{path}:{path.stat().st_mtime_ns}:{path.stat().st_size}"
    except OSError:
        marker = str(path)
    return hashlib.sha256(marker.encode("utf-8")).hexdigest()[:24]


def _image_thumbnail(path: Path, target: Path) -> bool:
    try:
        with ExitStack() as stack:
            opened_path = path
            if path.suffix.lower() in HEIC_SUFFIXES:
                temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix="wemute-heic-thumb-"))
                opened_path = Path(temporary) / "decoded.png"
                decode_heic(path, opened_path)
            image = stack.enter_context(Image.open(opened_path))
            image = ImageOps.exif_transpose(image)
            if getattr(image, "is_animated", False):
                image.seek(0)
            image.thumbnail((360, 240), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            background = Image.new("RGB", image.size, (31, 34, 38))
            if image.mode == "RGBA":
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image)
            background.save(target, format="JPEG", quality=88, optimize=True)
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _ffmpeg_thumbnail(path: Path, target: Path, kind: MediaKind) -> bool:
    executable = resolve_engine("ffmpeg")
    if not executable:
        return False
    if kind == MediaKind.VIDEO:
        command = [
            str(executable),
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "0",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=360:240:force_original_aspect_ratio=increase,crop=360:240",
            "-y",
            str(target),
        ]
    else:
        command = [
            str(executable),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-filter_complex",
            "aformat=channel_layouts=mono,showwavespic=s=360x180:colors=9EA3AA",
            "-frames:v",
            "1",
            "-y",
            str(target),
        ]
    try:
        subprocess.run(command, capture_output=True, timeout=18, check=True)
        return target.exists()
    except (OSError, subprocess.SubprocessError):
        return False


def create_thumbnail(path: Path, kind: MediaKind) -> str | None:
    if kind not in {MediaKind.IMAGE, MediaKind.AUDIO, MediaKind.VIDEO}:
        return None
    target = THUMBNAIL_ROOT / f"{_thumbnail_key(path)}.jpg"
    if target.exists():
        return str(target)
    success = (
        _image_thumbnail(path, target)
        if kind == MediaKind.IMAGE
        else _ffmpeg_thumbnail(path, target, kind)
    )
    return str(target) if success else None


def probe_file(path: Path, *, create_preview: bool = True) -> FileDescriptor:
    kind = media_kind_for(path)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    sample_rate: int | None = None
    channels: int | None = None

    if kind == MediaKind.IMAGE:
        if path.suffix.lower() in HEIC_SUFFIXES:
            try:
                dimensions = heic_dimensions(path)
                if dimensions:
                    width, height = dimensions
            except RuntimeError:
                pass
        else:
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except (OSError, ValueError):
                pass
    elif kind in {MediaKind.AUDIO, MediaKind.VIDEO}:
        payload = _ffprobe(path)
        streams = payload.get("streams", [])
        format_payload = payload.get("format", {})
        raw_duration = format_payload.get("duration")
        try:
            duration = float(raw_duration) if raw_duration is not None else None
        except (TypeError, ValueError):
            duration = None
        for stream in streams:
            if stream.get("codec_type") == "video" and width is None:
                width = int(stream.get("width") or 0) or None
                height = int(stream.get("height") or 0) or None
            if stream.get("codec_type") == "audio" and sample_rate is None:
                try:
                    sample_rate = int(stream.get("sample_rate") or 0) or None
                except (TypeError, ValueError):
                    sample_rate = None
                channels = int(stream.get("channels") or 0) or None

    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    thumbnail = create_thumbnail(path, kind) if create_preview else None
    return FileDescriptor(
        path=str(path),
        name=path.name,
        suffix=path.suffix.lower(),
        kind=kind,
        mime=mime,
        size=size,
        width=width,
        height=height,
        duration=duration,
        sample_rate=sample_rate,
        channels=channels,
        thumbnail_path=thumbnail,
    )
