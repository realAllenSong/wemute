from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from wemute.domain import MediaKind, OperationKind
from wemute.tools import is_group_tool, is_tool, tool_for


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
    package_ids: tuple[str, ...]
    target_format: str
    default_options: tuple[tuple[str, object], ...] = ()


ACTIONS: dict[OperationKind, ActionDefinition] = {
    OperationKind.REMOVE_BACKGROUND: ActionDefinition(
        OperationKind.REMOVE_BACKGROUND,
        "Remove Background",
        MediaKind.IMAGE,
        ".png",
        ("birefnet", "u2net"),
        "PNG",
    ),
    OperationKind.UPSCALE: ActionDefinition(
        OperationKind.UPSCALE,
        "Upscale 2×",
        MediaKind.IMAGE,
        ".png",
        ("realesrgan-photo",),
        "PNG",
        (("scale", 2),),
    ),
    OperationKind.ERASE_OBJECT: ActionDefinition(
        OperationKind.ERASE_OBJECT,
        "Erase Object",
        MediaKind.IMAGE,
        ".png",
        ("lama",),
        "PNG",
    ),
    OperationKind.SEPARATE_VOCALS: ActionDefinition(
        OperationKind.SEPARATE_VOCALS,
        "Separate Vocals",
        MediaKind.AUDIO,
        ".wav",
        ("mlx-audio-separator",),
        "WAV",
    ),
}

ACTION_CHOICES: tuple[ActionDefinition, ...] = (
    ACTIONS[OperationKind.REMOVE_BACKGROUND],
    ActionDefinition(
        OperationKind.UPSCALE,
        "Upscale Photo 2×",
        MediaKind.IMAGE,
        ".png",
        ("realesrgan-photo",),
        "PNG",
        (("scale", 2), ("style", "photo")),
    ),
    ActionDefinition(
        OperationKind.UPSCALE,
        "Upscale Photo 4×",
        MediaKind.IMAGE,
        ".png",
        ("realesrgan-photo",),
        "PNG",
        (("scale", 4), ("style", "photo")),
    ),
    ActionDefinition(
        OperationKind.UPSCALE,
        "Upscale Illustration 2×",
        MediaKind.IMAGE,
        ".png",
        ("realesrgan-photo",),
        "PNG",
        (("scale", 2), ("style", "illustration")),
    ),
    ActionDefinition(
        OperationKind.UPSCALE,
        "Upscale Illustration 4×",
        MediaKind.IMAGE,
        ".png",
        ("realesrgan-photo",),
        "PNG",
        (("scale", 4), ("style", "illustration")),
    ),
    ACTIONS[OperationKind.ERASE_OBJECT],
    ACTIONS[OperationKind.SEPARATE_VOCALS],
)

ACTION_BY_LABEL = {definition.label: definition for definition in ACTION_CHOICES}


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
    MediaKind.OTHER: [],
}

DEFAULT_BY_KIND: dict[MediaKind, str] = {
    MediaKind.IMAGE: "WebP",
    MediaKind.AUDIO: "WAV",
    MediaKind.VIDEO: "MP4 (H.265)" if platform.system() == "Darwin" else "MP4 (H.264)",
}


# ------------------------------------------------------------ files & documents


@dataclass(frozen=True, slots=True)
class FileTarget:
    """An output for a non-media kind. ``sources`` limits which inputs offer it."""

    label: str
    extension: str
    sources: frozenset[str] | None = None
    folder: bool = False


SOURCE_SUFFIXES: dict[MediaKind, frozenset[str]] = {
    MediaKind.DOCUMENT: frozenset(
        {".doc", ".docx", ".docm", ".dotx", ".odt", ".fodt", ".rtf", ".pages", ".wps"}
    ),
    MediaKind.SPREADSHEET: frozenset(
        {".xls", ".xlsx", ".xlsm", ".ods", ".fods", ".numbers", ".csv", ".tsv"}
    ),
    MediaKind.PRESENTATION: frozenset({".ppt", ".pptx", ".pps", ".ppsx", ".odp", ".key"}),
    MediaKind.PDF: frozenset({".pdf"}),
    MediaKind.EBOOK: frozenset({".epub", ".mobi", ".azw3", ".azw", ".fb2"}),
    MediaKind.ARCHIVE: frozenset(
        {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".tbz", ".tbz2", ".xz", ".txz"}
    ),
    MediaKind.DATA: frozenset({".json", ".md", ".markdown", ".html", ".htm", ".txt"}),
    MediaKind.FONT: frozenset({".ttf", ".otf", ".woff", ".woff2"}),
    MediaKind.VECTOR: frozenset({".svg"}),
}

_TABULAR = frozenset({".xlsx", ".xlsm", ".csv", ".tsv"})
_MARKDOWN = frozenset({".md", ".markdown"})
_HTML = frozenset({".html", ".htm"})

PER_PAGE_PNG = "PNG (per page)"
PER_PAGE_JPG = "JPG (per page)"
PER_SLIDE_PNG = "PNG (per slide)"
SMALLER_PDF = "Smaller PDF"
EXTRACT = "Folder"

FILE_TARGETS: dict[MediaKind, list[FileTarget]] = {
    MediaKind.DOCUMENT: [
        FileTarget("PDF", ".pdf"),
        FileTarget("DOCX", ".docx"),
        FileTarget("ODT", ".odt"),
        FileTarget("RTF", ".rtf"),
        FileTarget("TXT", ".txt"),
        FileTarget("HTML", ".html"),
    ],
    MediaKind.SPREADSHEET: [
        FileTarget("XLSX", ".xlsx"),
        FileTarget("CSV", ".csv"),
        FileTarget("PDF", ".pdf"),
        FileTarget("ODS", ".ods"),
        FileTarget("JSON", ".json"),
    ],
    MediaKind.PRESENTATION: [
        FileTarget("PDF", ".pdf"),
        FileTarget("PPTX", ".pptx"),
        FileTarget("ODP", ".odp"),
        FileTarget(PER_SLIDE_PNG, "", folder=True),
    ],
    MediaKind.PDF: [
        FileTarget("DOCX", ".docx"),
        FileTarget(PER_PAGE_PNG, "", folder=True),
        FileTarget(PER_PAGE_JPG, "", folder=True),
        FileTarget("TXT", ".txt"),
        FileTarget(SMALLER_PDF, ".pdf"),
    ],
    MediaKind.EBOOK: [
        FileTarget("PDF", ".pdf"),
        FileTarget("EPUB", ".epub"),
        FileTarget("MOBI", ".mobi"),
        FileTarget("AZW3", ".azw3"),
    ],
    MediaKind.ARCHIVE: [FileTarget(EXTRACT, "", folder=True)],
    MediaKind.DATA: [
        FileTarget("DOCX", ".docx", _MARKDOWN | _HTML | {".txt"}),
        FileTarget("CSV", ".csv", frozenset({".json"})),
        FileTarget("XLSX", ".xlsx", frozenset({".json"})),
        FileTarget("MD", ".md", _HTML | {".json"}),
        FileTarget("HTML", ".html", _MARKDOWN | {".txt", ".json"}),
        FileTarget("PDF", ".pdf", _MARKDOWN | _HTML | {".txt"}),
        FileTarget("TXT", ".txt", _MARKDOWN | _HTML),
    ],
    MediaKind.FONT: [
        FileTarget("WOFF2", ".woff2"),
        FileTarget("TTF", ".ttf"),
        FileTarget("OTF", ".otf"),
        FileTarget("WOFF", ".woff"),
    ],
    MediaKind.VECTOR: [FileTarget("PNG", ".png"), FileTarget("PDF", ".pdf")],
}

# One output from the whole group, in list order.
COMBINE_PDF = "One PDF"
MERGE_PDF = "Merged PDF"
PACK_ZIP = "One ZIP"
PACK_7Z = "One 7Z"
COMBINE_EXTENSIONS = {COMBINE_PDF: ".pdf", MERGE_PDF: ".pdf", PACK_ZIP: ".zip", PACK_7Z: ".7z"}


def combine_choices(kind: MediaKind) -> list[str]:
    if kind == MediaKind.OTHER:
        return []
    special = {MediaKind.IMAGE: [COMBINE_PDF], MediaKind.PDF: [MERGE_PDF]}.get(kind, [])
    return [*special, PACK_ZIP, PACK_7Z]


def is_combine(choice: str) -> bool:
    """One output from the whole group (merged PDFs, archives, group tools)."""
    return choice in COMBINE_EXTENSIONS or is_group_tool(choice)


def file_target(kind: MediaKind, label: str) -> FileTarget | None:
    return next((item for item in FILE_TARGETS.get(kind, []) if item.label == label), None)


def _offers(target: FileTarget, suffix: str) -> bool:
    if target.sources is not None and suffix not in target.sources:
        return False
    # Re-saving into the same format is a no-op, except deliberate rewrites.
    return target.label == SMALLER_PDF or target.extension != suffix


def file_targets_for(kind: MediaKind, suffix: str) -> list[str]:
    suffix = suffix.lower()
    return [item.label for item in FILE_TARGETS.get(kind, []) if _offers(item, suffix)]


def default_file_target(kind: MediaKind, suffix: str) -> str | None:
    suffix = suffix.lower()
    preferred = {
        MediaKind.DOCUMENT: "PDF",
        MediaKind.PRESENTATION: "PDF",
        MediaKind.PDF: "DOCX",
        MediaKind.EBOOK: "PDF",
        MediaKind.ARCHIVE: EXTRACT,
        MediaKind.VECTOR: "PNG",
    }.get(kind)
    if kind == MediaKind.SPREADSHEET:
        preferred = "XLSX" if suffix in {".csv", ".tsv"} else (
            "CSV" if suffix in {".xlsx", ".xlsm"} else "XLSX"
        )
    elif kind == MediaKind.DATA:
        preferred = {".json": "CSV", ".html": "MD", ".htm": "MD"}.get(suffix, "DOCX")
    elif kind == MediaKind.FONT:
        preferred = "TTF" if suffix in {".woff", ".woff2"} else "WOFF2"
    available = file_targets_for(kind, suffix)
    if preferred in available:
        return preferred
    return available[0] if available else None


def target_extension(kind: MediaKind, label: str) -> str | None:
    if is_tool(label):
        tool = tool_for(label)
        return (tool.extension or None) if tool else None
    if label in COMBINE_EXTENSIONS:
        return COMBINE_EXTENSIONS[label]
    if kind in FILE_TARGETS:
        target = file_target(kind, label)
        return target.extension if target else None
    definition = TARGETS.get(label)
    return definition.extension if definition else None


def options_for(
    kind: MediaKind,
    enabled_actions: set[OperationKind] | None = None,
    suffixes: set[str] | None = None,
) -> list[str]:
    """Plain outputs for a kind. With ``suffixes``, those any of the sources offer."""
    if kind in FILE_TARGETS:
        if suffixes is None:
            return [item.label for item in FILE_TARGETS[kind]]
        offered = {label for suffix in suffixes for label in file_targets_for(kind, suffix)}
        return [item.label for item in FILE_TARGETS[kind] if item.label in offered]
    options = list(OPTIONS_BY_KIND.get(kind, []))
    for action in enabled_actions or set():
        options.extend(
            definition.label
            for definition in ACTION_CHOICES
            if definition.id == action and definition.kind == kind
        )
    return options


def display_choice(operation: OperationKind, target_format: str) -> str:
    if operation == OperationKind.CONVERT:
        return target_format
    definition = ACTIONS.get(operation)
    return definition.label if definition else target_format


def display_job_choice(job) -> str:  # noqa: ANN001 - avoids a circular type import
    if job.operation == OperationKind.CONVERT:
        return job.target_format
    for definition in ACTION_CHOICES:
        if (
            definition.id == job.operation
            and dict(definition.default_options) == job.operation_options
        ):
            return definition.label
    return display_choice(job.operation, job.target_format)


def apply_choice(job, choice: str) -> bool:  # noqa: ANN001 - avoids a circular type import
    action = ACTION_BY_LABEL.get(choice)
    if action:
        if action.kind != job.source.kind:
            return False
        job.operation = action.id
        job.target_format = action.target_format
        job.operation_options = dict(action.default_options)
        return True
    if not is_compatible(job.source.kind, choice, job.source.suffix):
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
    if kind in FILE_TARGETS:
        return default_file_target(kind, source_suffix)
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


def is_compatible(kind: MediaKind, target: str, suffix: str | None = None) -> bool:
    """Whether ``target`` is an output of ``kind`` (and of that source format, if given)."""
    if is_tool(target):
        tool = tool_for(target)
        return bool(tool and kind in tool.kinds)
    if target in COMBINE_EXTENSIONS:
        return target in combine_choices(kind)
    if kind in FILE_TARGETS:
        item = file_target(kind, target)
        return bool(item and (suffix is None or _offers(item, suffix.lower())))
    definition = TARGETS.get(target)
    return bool(definition and definition.kind == kind)


def unique_output_path(
    source: Path,
    destination: Path,
    extension: str,
    suffix: str | None = None,
    stem: str | None = None,
    plain: bool = False,
) -> Path:
    stem = (stem or source.stem) + _OUTPUT_TAG
    same_extension = not plain and not _OUTPUT_TAG and source.suffix.lower() == extension.lower()
    base = f"{stem}{suffix}" if suffix else (
        f"{stem} converted" if same_extension else stem
    )
    candidate = destination / f"{base}{extension}"
    number = 2
    while (
        candidate.exists()
        or candidate.resolve() == source.resolve()
        or candidate.resolve() in _RESERVED_OUTPUTS
    ):
        candidate = destination / f"{base} {number}{extension}"
        number += 1
    _RESERVED_OUTPUTS.add(candidate.resolve())
    return candidate


# 设置 · 文件命名: appended to every output name ("IMG_0412-wemute.jpg") when set.
_OUTPUT_TAG = ""


def set_output_tag(tag: str) -> None:
    global _OUTPUT_TAG
    _OUTPUT_TAG = tag


# Jobs run in parallel, so a name chosen for one job must stay unavailable to the
# others until that job finalizes or discards its output.
_RESERVED_OUTPUTS: set[Path] = set()


def release_output(path: Path) -> None:
    _RESERVED_OUTPUTS.discard(path.resolve())
