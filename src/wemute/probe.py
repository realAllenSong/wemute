from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
import tempfile
import zipfile
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
_ZIP_MEMBERS = (
    ("word/document.xml", ".docx"),
    ("xl/workbook.xml", ".xlsx"),
    ("ppt/presentation.xml", ".pptx"),
)
_OPEN_DOCUMENT = {
    "application/vnd.oasis.opendocument.text": ".odt",
    "application/vnd.oasis.opendocument.spreadsheet": ".ods",
    "application/vnd.oasis.opendocument.presentation": ".odp",
    "application/epub+zip": ".epub",
}
_MIME_SUFFIXES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/rtf": ".rtf",
    "text/rtf": ".rtf",
    "application/zip": ".zip",
    "application/x-7z-compressed": ".7z",
    "application/x-rar": ".rar",
    "application/vnd.rar": ".rar",
    "application/x-tar": ".tar",
    "application/gzip": ".gz",
    "application/x-gzip": ".gz",
    "application/x-bzip2": ".bz2",
    "application/x-xz": ".xz",
    "application/json": ".json",
    "text/html": ".html",
    "text/csv": ".csv",
    "image/svg+xml": ".svg",
    "font/ttf": ".ttf",
    "font/sfnt": ".ttf",
    "font/otf": ".otf",
    "font/woff": ".woff",
    "font/woff2": ".woff2",
    "application/epub+zip": ".epub",
}


def _kind_for_suffix(suffix: str) -> MediaKind:
    from wemute.capabilities import SOURCE_SUFFIXES

    if suffix in IMAGE_SUFFIXES:
        return MediaKind.IMAGE
    if suffix in AUDIO_SUFFIXES:
        return MediaKind.AUDIO
    if suffix in VIDEO_SUFFIXES:
        return MediaKind.VIDEO
    for kind, suffixes in SOURCE_SUFFIXES.items():
        if suffix in suffixes:
            return kind
    return MediaKind.OTHER


def _sniff_zip(path: Path) -> str:
    import zipfile

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "mimetype" in names:
                mimetype = archive.read("mimetype").decode("ascii", "ignore").strip()
                if mimetype in _OPEN_DOCUMENT:
                    return _OPEN_DOCUMENT[mimetype]
            for member, suffix in _ZIP_MEMBERS:
                if member in names:
                    return suffix
    except (OSError, zipfile.BadZipFile, ValueError):
        return ""
    return ".zip"


def sniff_suffix(path: Path) -> str:
    """Identify a file by its content: magic bytes, zip contents, then `file`."""
    try:
        with path.open("rb") as handle:
            head = handle.read(512)
    except OSError:
        return ""
    if head.startswith(b"%PDF-"):
        return ".pdf"
    if head.startswith(b"PK\x03\x04"):
        return _sniff_zip(path)
    if head.startswith(b"7z\xbc\xaf\x27\x1c"):
        return ".7z"
    if head.startswith(b"Rar!\x1a\x07"):
        return ".rar"
    if head.startswith(b"\x1f\x8b"):
        return ".gz"
    if head.startswith(b"BZh"):
        return ".bz2"
    if head.startswith(b"\xfd7zXZ\x00"):
        return ".xz"
    if len(head) > 262 and head[257:262] == b"ustar":
        return ".tar"
    if head.startswith(b"wOF2"):
        return ".woff2"
    if head.startswith(b"wOFF"):
        return ".woff"
    if head.startswith(b"OTTO"):
        return ".otf"
    if head.startswith(b"\x00\x01\x00\x00") or head.startswith(b"true"):
        return ".ttf"
    if head.startswith(b"{\\rtf"):
        return ".rtf"
    text = head.lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if text.startswith(b"<svg") or (text.startswith(b"<?xml") and b"<svg" in head.lower()):
        return ".svg"
    try:
        result = subprocess.run(
            ["/usr/bin/file", "--brief", "--mime-type", str(path)],
            capture_output=True,
            timeout=5,
            check=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return _MIME_SUFFIXES.get(result.stdout.strip(), "")


def effective_suffix(path: Path) -> str:
    """The suffix that decides the kind; sniffed when the name does not say."""
    suffix = path.suffix.lower()
    if suffix and _kind_for_suffix(suffix) != MediaKind.OTHER:
        return suffix
    sniffed = sniff_suffix(path)
    return sniffed or suffix


def media_kind_for(path: Path) -> MediaKind:
    return _kind_for_suffix(effective_suffix(path))


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
        marker = f"v2:{path}:{path.stat().st_mtime_ns}:{path.stat().st_size}"
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
            # Transparent mid-grey waveform that reads on light and dark tiles.
            "aformat=channel_layouts=mono,showwavespic=s=360x180:colors=0x8A909A",
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


_QUICK_LOOK_KINDS = {
    MediaKind.DOCUMENT,
    MediaKind.SPREADSHEET,
    MediaKind.PRESENTATION,
    MediaKind.PDF,
    MediaKind.VECTOR,
    MediaKind.FONT,
}


def _epub_cover(path: Path, target: Path) -> bool:
    """The cover image inside an EPUB (Quick Look can stall for seconds on books)."""
    try:
        with zipfile.ZipFile(path) as book:
            images = [
                name
                for name in book.namelist()
                if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            ]
            covers = [name for name in images if "cover" in name.lower()] or images
            if not covers:
                return False
            with book.open(covers[0]) as handle, Image.open(handle) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((360, 360))
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target, "JPEG", quality=85)
        return True
    except (OSError, ValueError, zipfile.BadZipFile, Image.DecompressionBombError):
        return False


def _quick_look_thumbnail(path: Path, target: Path) -> bool:
    """Ask Quick Look for the same preview Finder shows (documents, PDFs, fonts…)."""
    qlmanage = Path("/usr/bin/qlmanage")
    if not qlmanage.exists():
        return False
    with tempfile.TemporaryDirectory(prefix="wemute-ql-") as scratch:
        try:
            subprocess.run(
                [str(qlmanage), "-t", "-s", "360", "-o", scratch, str(path)],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        produced = next(Path(scratch).glob("*.png"), None)
        if not produced:
            return False
        try:
            with Image.open(produced) as image:
                image = image.convert("RGBA")
                # Quick Look returns generic icons for unknown content; those are
                # mostly transparent. Real previews are opaque pages.
                alpha = image.getchannel("A")
                if sum(alpha.histogram()[250:]) < alpha.width * alpha.height * 0.4:
                    return False
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=alpha)
                background.save(target, format="JPEG", quality=88)
            return True
        except (OSError, ValueError):
            return False


def create_thumbnail(path: Path, kind: MediaKind) -> str | None:
    if kind in _QUICK_LOOK_KINDS:
        target = THUMBNAIL_ROOT / f"{_thumbnail_key(path)}-ql.jpg"
        if target.exists():
            return str(target)
        return str(target) if _quick_look_thumbnail(path, target) else None
    if kind == MediaKind.EBOOK and path.suffix.lower() == ".epub":
        target = THUMBNAIL_ROOT / f"{_thumbnail_key(path)}-cover.jpg"
        if target.exists():
            return str(target)
        return str(target) if _epub_cover(path, target) else None
    if kind not in {MediaKind.IMAGE, MediaKind.AUDIO, MediaKind.VIDEO}:
        return None
    suffix = ".png" if kind == MediaKind.AUDIO else ".jpg"
    target = THUMBNAIL_ROOT / f"{_thumbnail_key(path)}{suffix}"
    if target.exists():
        return str(target)
    success = (
        _image_thumbnail(path, target)
        if kind == MediaKind.IMAGE
        else _ffmpeg_thumbnail(path, target, kind)
    )
    return str(target) if success else None


def probe_file(path: Path, *, create_preview: bool = True) -> FileDescriptor:
    suffix = effective_suffix(path)
    kind = _kind_for_suffix(suffix)
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
        suffix=suffix,
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
