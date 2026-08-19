from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class MediaKind(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ImageOptions:
    scale_percent: int = 100
    max_edge: int | None = None
    quality: int = 84
    corner_radius: int = 0


@dataclass(slots=True)
class FileDescriptor:
    path: str
    name: str
    suffix: str
    kind: MediaKind
    mime: str = "application/octet-stream"
    size: int = 0
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    thumbnail_path: str | None = None

    @property
    def source_format(self) -> str:
        return self.suffix.removeprefix(".").upper() or "FILE"


@dataclass(slots=True)
class JobRecord:
    id: str
    source: FileDescriptor
    target_format: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    output_path: str | None = None
    output_size: int | None = None
    error: str | None = None
    selected: bool = False
    created_at: float = 0.0
    image_options: ImageOptions = field(default_factory=ImageOptions)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source"]["kind"] = self.source.kind.value
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobRecord":
        source_payload = dict(payload["source"])
        source_payload["kind"] = MediaKind(source_payload["kind"])
        image_options = ImageOptions(**payload.get("image_options", {}))
        status = JobStatus(payload.get("status", JobStatus.QUEUED))
        if status == JobStatus.RUNNING:
            status = JobStatus.QUEUED
        return cls(
            id=payload["id"],
            source=FileDescriptor(**source_payload),
            target_format=payload["target_format"],
            status=status,
            progress=float(payload.get("progress", 0.0)),
            output_path=payload.get("output_path"),
            output_size=payload.get("output_size"),
            error=payload.get("error"),
            selected=bool(payload.get("selected", False)),
            created_at=float(payload.get("created_at", 0.0)),
            image_options=image_options,
        )


@dataclass(slots=True)
class ConversionPlan:
    job_id: str
    source: Path
    temporary_output: Path
    final_output: Path
    command: list[str] = field(default_factory=list)
