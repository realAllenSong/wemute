from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from wemute.domain import MediaKind, OperationKind


@dataclass(frozen=True, slots=True)
class TargetDefinition:
    label: str
    extension: str
    kind: MediaKind
    codec: str | None = None
    container: str | None = None


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    id: OperationKind
    label: str
    kind: MediaKind
    output_extension: str
    package_id: str
    target_format: str
    default_options: tuple[tuple[str, object], ...] = ()


ACTIONS: dict[OperationKind, ActionDefinition] = {
    OperationKind.REMOVE_BACKGROUND: ActionDefinition(
        OperationKind.REMOVE_BACKGROUND,
        "Remove Background",
        MediaKind.IMAGE,
        ".png",
        "u2net",
        "PNG",
    ),
    OperationKind.UPSCALE: ActionDefinition(
        OperationKind.UPSCALE,
        "Upscale 2×",
        MediaKind.IMAGE,
        ".png",
        "realesrgan-photo",
        "PNG",
        (("scale", 2),),
    ),
    OperationKind.ERASE_OBJECT: ActionDefinition(
        OperationKind.ERASE_OBJECT,
        "Erase Object",
        MediaKind.IMAGE,
        ".png",
        "lama",
        "PNG",
    ),
    OperationKind.SEPARATE_VOCALS: ActionDefinition(
        OperationKind.SEPARATE_VOCALS,
        "Separate Vocals",
        MediaKind.AUDIO,
        ".wav",
        "mlx-audio-separator",
        "WAV",
    ),
}

ACTION_BY_LABEL = {definition.label: definition for definition in ACTIONS.values()}


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


def options_for(
    kind: MediaKind,
    enabled_actions: set[OperationKind] | None = None,
) -> list[str]:
    options = list(OPTIONS_BY_KIND.get(kind, []))
    for action in enabled_actions or set():
        definition = ACTIONS.get(action)
        if definition and definition.kind == kind:
            options.append(definition.label)
    return options


def display_choice(operation: OperationKind, target_format: str) -> str:
    if operation == OperationKind.CONVERT:
        return target_format
    definition = ACTIONS.get(operation)
    return definition.label if definition else target_format


def apply_choice(job, choice: str) -> bool:  # noqa: ANN001 - avoids a circular type import
    action = ACTION_BY_LABEL.get(choice)
    if action:
        if action.kind != job.source.kind:
            return False
        job.operation = action.id
        job.target_format = action.target_format
        job.operation_options = dict(action.default_options)
        return True
    if not is_compatible(job.source.kind, choice):
        return False
    job.operation = OperationKind.CONVERT
    job.target_format = choice
    job.operation_options = {}
    return True


def is_choice_compatible(
    kind: MediaKind,
    choice: str,
    enabled_actions: set[OperationKind] | None = None,
) -> bool:
    action = ACTION_BY_LABEL.get(choice)
    if action:
        return action.kind == kind and action.id in (enabled_actions or set())
    return is_compatible(kind, choice)


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


def unique_output_path(
    source: Path,
    destination: Path,
    extension: str,
    suffix: str | None = None,
) -> Path:
    same_extension = source.suffix.lower() == extension.lower()
    base = f"{source.stem}{suffix}" if suffix else (
        f"{source.stem} converted" if same_extension else source.stem
    )
    candidate = destination / f"{base}{extension}"
    number = 2
    while candidate.exists() or candidate.resolve() == source.resolve():
        candidate = destination / f"{base} {number}{extension}"
        number += 1
    return candidate
