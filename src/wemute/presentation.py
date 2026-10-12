from __future__ import annotations

import math
from pathlib import Path

from wemute.domain import FileDescriptor, JobRecord, JobStatus, MediaKind


GROUP_LABELS = {
    "en": {
        MediaKind.IMAGE: "Images",
        MediaKind.AUDIO: "Audio",
        MediaKind.VIDEO: "Video",
        MediaKind.DOCUMENT: "Documents",
        MediaKind.OTHER: "Other",
    },
    "zh": {
        MediaKind.IMAGE: "图片",
        MediaKind.AUDIO: "音频",
        MediaKind.VIDEO: "视频",
        MediaKind.DOCUMENT: "文档",
        MediaKind.OTHER: "其他",
    },
}

GROUP_ORDER = {
    MediaKind.IMAGE: 0,
    MediaKind.AUDIO: 1,
    MediaKind.VIDEO: 2,
    MediaKind.DOCUMENT: 3,
    MediaKind.OTHER: 4,
}


def format_bytes(value: int | None) -> str:
    if value is None:
        return "—"
    amount = float(value)
    units = ("B", "KB", "MB", "GB", "TB")
    index = 0
    while amount >= 1000 and index < len(units) - 1:
        amount /= 1000
        index += 1
    if index == 0:
        return f"{int(amount)} {units[index]}"
    return f"{amount:.1f} {units[index]}"


def format_duration(seconds: float | None) -> str | None:
    if seconds is None or not math.isfinite(seconds):
        return None
    rounded = max(0, int(round(seconds)))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def metadata_line(source: FileDescriptor) -> str:
    parts = [format_bytes(source.size)]
    if source.width and source.height:
        parts.append(f"{source.width} × {source.height}")
    duration = format_duration(source.duration)
    if duration:
        parts.append(duration)
    if source.sample_rate and source.kind == MediaKind.AUDIO:
        parts.append(f"{source.sample_rate / 1000:g} kHz")
    return "  ·  ".join(parts)


def status_title(status: JobStatus, language: str = "en") -> str:
    messages = {
        "en": {
            JobStatus.QUEUED: "Queued",
            JobStatus.RUNNING: "Converting…",
            JobStatus.SUCCEEDED: "Completed",
            JobStatus.FAILED: "Failed",
            JobStatus.CANCELLED: "Cancelled",
        },
        "zh": {
            JobStatus.QUEUED: "排队中",
            JobStatus.RUNNING: "正在转换…",
            JobStatus.SUCCEEDED: "已完成",
            JobStatus.FAILED: "转换失败",
            JobStatus.CANCELLED: "已取消",
        },
    }
    return messages.get(language, messages["en"])[status]


def output_summary(job: JobRecord, language: str = "en") -> str:
    if job.status == JobStatus.SUCCEEDED and job.output_size is not None:
        before = max(job.source.size, 1)
        after = job.output_size
        difference = round((1 - after / before) * 100)
        if difference > 0:
            if language == "zh":
                return f"{format_bytes(before)}  →  {format_bytes(after)}（缩小 {difference}%）"
            return f"{format_bytes(before)}  →  {format_bytes(after)} ({difference}% smaller)"
        return f"{format_bytes(before)}  →  {format_bytes(after)}"
    if job.status == JobStatus.RUNNING:
        converted = int(job.source.size * job.progress)
        joiner = " / " if language == "zh" else " of "
        return f"{format_bytes(converted)}{joiner}{format_bytes(job.source.size)}"
    if job.status == JobStatus.FAILED:
        return job.error or ("转换失败" if language == "zh" else "Conversion failed")
    if job.status == JobStatus.CANCELLED:
        return "已取消" if language == "zh" else "Cancelled"
    return "等待转换" if language == "zh" else "Waiting to convert"


def thumbnail_url(source: FileDescriptor) -> str:
    if source.thumbnail_path and Path(source.thumbnail_path).exists():
        return Path(source.thumbnail_path).as_uri()
    return "image://icons/file"


def _names(names: list[str], language: str) -> str:
    shown = names[:3]
    joiner = "、" if language == "zh" else ", "
    text = joiner.join(shown)
    if len(names) > len(shown):
        more = len(names) - len(shown)
        text += f" 等 {len(names)} 个" if language == "zh" else f" and {more} more"
    return text


def intake_notice(
    unsupported: list[str],
    unreadable: list[str],
    duplicates: int,
    language: str = "en",
) -> tuple[str, str]:
    """Explain files that were dropped but did not join the queue."""
    zh = language == "zh"
    parts: list[str] = []
    if unsupported:
        parts.append(
            f"已跳过不支持的文件：{_names(unsupported, language)}"
            if zh
            else f"Skipped unsupported: {_names(unsupported, language)}"
        )
    if unreadable:
        parts.append(
            f"无法读取：{_names(unreadable, language)}"
            if zh
            else f"Couldn't read: {_names(unreadable, language)}"
        )
    if duplicates:
        parts.append(
            f"{duplicates} 个文件已在列表中"
            if zh
            else f"{duplicates} already in the list"
        )
    kind = "error" if unreadable else "info"
    return ("  ·  " if not zh else "；").join(parts), kind


def batch_notice(
    succeeded: int,
    failed: int,
    source_bytes: int,
    output_bytes: int,
    language: str = "en",
) -> tuple[str, str]:
    zh = language == "zh"
    if failed and not succeeded:
        return (
            (f"{failed} 个文件转换失败" if zh else f"{failed} failed — see the rows for details"),
            "error",
        )
    if zh:
        text = f"已完成 {succeeded} 个文件"
    else:
        text = f"Converted {succeeded} file{'s' if succeeded != 1 else ''}"
    saved = source_bytes - output_bytes
    if succeeded and source_bytes and saved > 0:
        percent = round(saved / source_bytes * 100)
        text += (
            f"，节省 {format_bytes(saved)}（{percent}%）"
            if zh
            else f" · saved {format_bytes(saved)} ({percent}%)"
        )
    if failed:
        text += f"；{failed} 个失败" if zh else f" · {failed} failed"
        return text, "error"
    return text, "success"


def progress_summary(done: int, total: int, language: str = "en") -> str:
    if language == "zh":
        return f"正在转换 {done}/{total}"
    return f"Converting {done} of {total}"
