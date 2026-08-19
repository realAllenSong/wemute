from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from wemute.domain import MediaKind


@dataclass(frozen=True, slots=True)
class TargetDefinition:
    label: str
    extension: str
    kind: MediaKind
    codec: str | None = None
    container: str | None = None


TARGETS: dict[str, TargetDefinition] = {
    "JPEG": TargetDefinition("JPEG", ".jpg", MediaKind.IMAGE, "mjpeg"),
    "PNG": TargetDefinition("PNG", ".png", MediaKind.IMAGE, "png"),
    "WebP": TargetDefinition("WebP", ".webp", MediaKind.IMAGE, "libwebp"),
    "HEIC": TargetDefinition("HEIC", ".heic", MediaKind.IMAGE, "heif"),
    "AVIF": TargetDefinition("AVIF", ".avif", MediaKind.IMAGE, "avif"),
    "TIFF": TargetDefinition("TIFF", ".tiff", MediaKind.IMAGE, "tiff"),
    "BMP": TargetDefinition("BMP", ".bmp", MediaKind.IMAGE, "bmp"),
    "GIF": TargetDefinition("GIF", ".gif", MediaKind.IMAGE, "gif"),
    "MP3": TargetDefinition("MP3", ".mp3", MediaKind.AUDIO, "libmp3lame"),
    "WAV": TargetDefinition("WAV", ".wav", MediaKind.AUDIO, "pcm_s24le"),
    "FLAC": TargetDefinition("FLAC", ".flac", MediaKind.AUDIO, "flac"),
    "M4A (AAC)": TargetDefinition("M4A (AAC)", ".m4a", MediaKind.AUDIO, "aac"),
    "AIFF": TargetDefinition("AIFF", ".aiff", MediaKind.AUDIO, "pcm_s24be"),
    "OGG": TargetDefinition("OGG", ".ogg", MediaKind.AUDIO, "vorbis"),
    "Opus": TargetDefinition("Opus", ".opus", MediaKind.AUDIO, "libopus"),
    "MP4 (H.264)": TargetDefinition("MP4 (H.264)", ".mp4", MediaKind.VIDEO, "h264"),
    "MP4 (H.265)": TargetDefinition("MP4 (H.265)", ".mp4", MediaKind.VIDEO, "hevc"),
    "MOV (ProRes)": TargetDefinition("MOV (ProRes)", ".mov", MediaKind.VIDEO, "prores_ks"),
    "MKV (H.264)": TargetDefinition("MKV (H.264)", ".mkv", MediaKind.VIDEO, "h264"),
    "WebM (VP9)": TargetDefinition("WebM (VP9)", ".webm", MediaKind.VIDEO, "libvpx-vp9"),
    "Animated GIF": TargetDefinition("Animated GIF", ".gif", MediaKind.VIDEO, "gif"),
}

OPTIONS_BY_KIND: dict[MediaKind, list[str]] = {
    MediaKind.IMAGE: ["WebP", "JPEG", "PNG", "HEIC", "AVIF", "TIFF", "GIF", "BMP"],
    MediaKind.AUDIO: ["WAV", "FLAC", "MP3", "M4A (AAC)", "AIFF", "OGG", "Opus"],
    MediaKind.VIDEO: [
        "MP4 (H.265)",
        "MP4 (H.264)",
        "MOV (ProRes)",
        "MKV (H.264)",
        "WebM (VP9)",
        "Animated GIF",
    ],
    MediaKind.DOCUMENT: [],
    MediaKind.OTHER: [],
}

DEFAULT_BY_KIND: dict[MediaKind, str] = {
    MediaKind.IMAGE: "WebP",
    MediaKind.AUDIO: "WAV",
    MediaKind.VIDEO: "MP4 (H.265)" if platform.system() == "Darwin" else "MP4 (H.264)",
}


def options_for(kind: MediaKind) -> list[str]:
    return list(OPTIONS_BY_KIND.get(kind, []))


def default_target(kind: MediaKind, source_suffix: str) -> str | None:
    options = options_for(kind)
    if not options:
        return None
    preferred = DEFAULT_BY_KIND[kind]
    target = TARGETS[preferred]
    if source_suffix.lower() == target.extension:
        return options[1] if len(options) > 1 else preferred
    return preferred


def target_definition(label: str) -> TargetDefinition:
    return TARGETS[label]


def is_compatible(kind: MediaKind, target: str) -> bool:
    definition = TARGETS.get(target)
    return bool(definition and definition.kind == kind)


def unique_output_path(source: Path, destination: Path, extension: str) -> Path:
    same_extension = source.suffix.lower() == extension.lower()
    base = f"{source.stem} converted" if same_extension else source.stem
    candidate = destination / f"{base}{extension}"
    number = 2
    while candidate.exists() or candidate.resolve() == source.resolve():
        candidate = destination / f"{base} {number}{extension}"
        number += 1
    return candidate
