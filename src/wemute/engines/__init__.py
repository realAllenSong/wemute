"""Converters for documents, PDFs, e-books, archives, data, fonts and vectors.

Every conversion runs in a worker process (``wemute.convert_worker``) so the
scheduler can cancel it, read its progress and keep the UI responsive.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from wemute.capabilities import (
    COMBINE_EXTENSIONS,
    COMBINE_PDF,
    MERGE_PDF,
    PACK_7Z,
    PER_PAGE_JPG,
    PER_PAGE_PNG,
    PER_SLIDE_PNG,
    SMALLER_PDF,
    file_target,
    is_combine,
    unique_output_path,
)
from wemute.domain import ConversionPlan, JobRecord, MediaKind
from wemute.engines.archive import archive_stem
from wemute.tools import SPEECH_ENGINES, TOOL_BY_KEY, TRIAGE_FOLDER, is_tool, name_suffix, tool_for

TABULAR_SUFFIXES = {".xlsx", ".xlsm", ".csv", ".tsv"}

# Lanes and how many jobs each runs at once. LibreOffice and Calibre are heavy
# and share profile state, so they run one at a time. Vision shares the Neural
# Engine and GPU, so two at once keeps the machine responsive. ThunderTalk
# loads a speech model per run, so one at a time.
LANE_LIMITS = {"office": 1, "ebook": 1, "files": 2, "vision": 2, "speech": 1}


@dataclass(frozen=True, slots=True)
class Route:
    engine: str
    component: str | None
    lane: str


class ComponentMissing(RuntimeError):
    def __init__(self, component: str) -> None:
        super().__init__(f"Component not installed: {component}")
        self.component = component


def route(kind: MediaKind, suffix: str, target: str) -> Route:
    suffix = suffix.lower()
    if is_tool(target):
        if TOOL_BY_KEY[target].engine in SPEECH_ENGINES:
            return Route("speech", None, "speech")
        return Route("vision", None, "vision")
    if is_combine(target):
        return Route("combine", None, "files")
    if kind == MediaKind.DOCUMENT:
        return Route("office", "libreoffice", "office")
    if kind == MediaKind.SPREADSHEET:
        if target in {"XLSX", "CSV", "JSON"} and suffix in TABULAR_SUFFIXES:
            return Route("table", None, "files")
        if target in {"CSV", "JSON"}:
            return Route("office_table", "libreoffice", "office")
        return Route("office", "libreoffice", "office")
    if kind == MediaKind.PRESENTATION:
        engine = "office_slides" if target == PER_SLIDE_PNG else "office"
        return Route(engine, "libreoffice", "office")
    if kind == MediaKind.PDF:
        return Route("pdf", None, "files")
    if kind == MediaKind.EBOOK:
        return Route("ebook", "calibre", "ebook")
    if kind == MediaKind.ARCHIVE:
        return Route("archive", None, "files")
    if kind == MediaKind.DATA:
        if suffix == ".json":
            return Route("table", None, "files")
        needs_pandoc = target == "MD" or (target == "DOCX" and suffix != ".txt")
        return Route("text", "pandoc" if needs_pandoc else None, "files")
    if kind == MediaKind.FONT:
        return Route("font", None, "files")
    if kind == MediaKind.VECTOR:
        return Route("vector", None, "files")
    raise ValueError(f"No converter for {kind.value} files")


def required_component(job: JobRecord) -> str | None:
    if job.source.kind in {MediaKind.IMAGE, MediaKind.AUDIO, MediaKind.VIDEO} and not is_combine(
        job.target_format
    ):
        return None
    try:
        return route(job.source.kind, job.source.suffix, job.target_format).component
    except ValueError:
        return None


def lane_for(job: JobRecord) -> str:
    return route(job.source.kind, job.source.suffix, job.target_format).lane


def combined_name(sources: list[Path]) -> str:
    """Name a combined output after the shared folder, else "first +N"."""
    parents = {source.parent for source in sources}
    if len(parents) == 1:
        parent = next(iter(parents))
        if parent.name and parent != Path.home():
            return parent.name
    first = sources[0]
    return first.stem if len(sources) == 1 else f"{first.stem} +{len(sources) - 1}"


def worker_command(request: dict) -> list[str]:
    payload = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
    if getattr(sys, "frozen", False):
        return [sys.executable, "--convert-worker", payload]
    return [sys.executable, "-m", "wemute.convert_worker", payload]


def _temporary_for(final: Path, job_id: str, folder: bool) -> Path:
    if folder:
        return final.with_name(f".{final.name}.wemute-{job_id[:8]}")
    return final.with_name(f".{final.stem}.wemute-{job_id[:8]}{final.suffix}")


def plan_file_job(
    job: JobRecord,
    destination: Path,
    *,
    members: list[JobRecord] | None = None,
    tools: dict[str, str] | None = None,
    language: str = "en",
    office_profile: Path | None = None,
    calibre_config: Path | None = None,
) -> ConversionPlan:
    """Plan a document-like conversion; ``members`` are the jobs of a combined output."""
    tools = tools or {}
    kind, suffix, target = job.source.kind, job.source.suffix.lower(), job.target_format
    chosen = route(kind, suffix, target)
    if chosen.component and chosen.component not in tools:
        raise ComponentMissing(chosen.component)
    destination.mkdir(parents=True, exist_ok=True)
    source = Path(job.source.path)
    jobs = members or [job]
    sources = [Path(item.source.path) for item in jobs]
    if chosen.engine in {"vision", "speech"}:
        return _plan_tool(job, destination, sources, language)

    folder = False
    if chosen.engine == "combine":
        extension = COMBINE_EXTENSIONS[target]
        name = combined_name(sources)
        final = unique_output_path(source, destination, extension, stem=name, plain=True)
    else:
        definition = file_target(kind, target)
        if definition is None:
            raise ValueError(f"{target} is not an output for {kind.value} files")
        folder = definition.folder
        if definition.folder:
            stem = archive_stem(source) if kind == MediaKind.ARCHIVE else source.stem
            final = unique_output_path(source, destination, "", stem=stem)
        elif target == SMALLER_PDF:
            final = unique_output_path(source, destination, ".pdf", suffix=" compressed")
        else:
            final = unique_output_path(source, destination, definition.extension)
    temporary = _temporary_for(final, job.id, folder)

    if chosen.engine == "combine":
        engine = {COMBINE_PDF: "images_pdf", MERGE_PDF: "merge_pdf"}.get(target, "pack")
    else:
        engine = chosen.engine
    request = {
        "engine": engine,
        "target": target,
        "extension": final.suffix,
        "sources": [str(path) for path in sources],
        "source_suffix": suffix,
        "output": str(temporary),
        "stem": final.name if folder else final.stem,
        "language": language,
        "tools": {key: value for key, value in tools.items() if key == chosen.component},
        "archive_format": "7z" if target == PACK_7Z else "zip",
        "image_format": "JPEG" if target == PER_PAGE_JPG else "PNG",
    }
    if chosen.component == "libreoffice" and office_profile:
        request["office_profile"] = str(office_profile)
    if chosen.component == "calibre" and calibre_config:
        request["calibre_config"] = str(calibre_config)
    return ConversionPlan(
        job.id, source, temporary, final, worker_command(request), folder_output=folder
    )


def _plan_tool(job: JobRecord, destination: Path, sources: list[Path], language: str) -> ConversionPlan:
    from wemute.engines.vision_io import photo_extension

    tool = tool_for(job.target_format)
    if tool is None or job.source.kind not in tool.kinds:
        raise ValueError(f"{job.target_format} is not available for {job.source.kind.value} files")
    source = sources[0]
    extension = tool.extension or photo_extension(source.suffix)
    if tool.folder:
        name = TRIAGE_FOLDER.get(language, TRIAGE_FOLDER["en"])
        final = unique_output_path(source, destination, "", stem=name, plain=True)
    elif tool.group:
        final = unique_output_path(source, destination, extension, stem=combined_name(sources), plain=True)
    else:
        suffix = name_suffix(tool, language, job.source.kind)
        final = unique_output_path(source, destination, extension, suffix=suffix or None)
    temporary = _temporary_for(final, job.id, tool.folder)
    request = {
        "engine": "speech" if tool.engine in SPEECH_ENGINES else "vision",
        "tool": tool.engine,
        "options": dict(tool.options),
        "group": tool.group,
        "sources": [str(path) for path in sources],
        "source_kind": job.source.kind.value,
        "output": str(temporary),
        "extension": extension,
        "language": language,
    }
    if tool.engine in SPEECH_ENGINES:
        from wemute.integrations import thundertalk_binary

        request["thundertalk"] = str(thundertalk_binary())
        request["source_suffix"] = source.suffix.lower()
    return ConversionPlan(
        job.id, source, temporary, final, worker_command(request), folder_output=tool.folder
    )


__all__ = [
    "ComponentMissing",
    "LANE_LIMITS",
    "PER_PAGE_PNG",
    "Route",
    "lane_for",
    "plan_file_job",
    "required_component",
    "route",
]
