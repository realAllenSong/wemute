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
        return f"正在转换 {done} / {total}"
    return f"Converting {done} of {total}"


# The sentence reads image → video → audio, independent of the list order.
SENTENCE_ORDER = (MediaKind.IMAGE, MediaKind.VIDEO, MediaKind.AUDIO)

_COUNT_UNITS = {
    "zh": {
        MediaKind.IMAGE: ("张图片", "张图片"),
        MediaKind.VIDEO: ("个视频", "个视频"),
        MediaKind.AUDIO: ("段音频", "段音频"),
    },
    "en": {
        MediaKind.IMAGE: ("image", "images"),
        MediaKind.VIDEO: ("video", "videos"),
        MediaKind.AUDIO: ("audio file", "audio files"),
    },
}


def count_phrase(kind: MediaKind, count: int, language: str = "en") -> str:
    """"12 张图片", "2 videos", "1 audio file"."""
    units = _COUNT_UNITS.get(language, _COUNT_UNITS["en"])
    fallback = ("个文件", "个文件") if language == "zh" else ("file", "files")
    singular, plural = units.get(kind, fallback)
    return f"{count} {singular if count == 1 else plural}"


def done_title(succeeded: int, failed: int, language: str = "en") -> str:
    zh = language == "zh"
    if failed and not succeeded:
        if zh:
            return f"{failed} 个文件转换失败"
        return f"{failed} file{'s' if failed != 1 else ''} failed"
    if failed:
        return f"{succeeded} 个已完成，{failed} 个失败" if zh else f"{succeeded} done, {failed} failed"
    if zh:
        return "1 个文件转好了" if succeeded == 1 else f"{succeeded} 个文件都转好了"
    return "Your file is ready" if succeeded == 1 else f"All {succeeded} files are ready"


def savings_parts(before: int, after: int, language: str = "en") -> tuple[str, str, bool]:
    """Lead text, highlighted amount, and whether the amount is a saving."""
    if before <= 0 or after <= 0:
        return "", "", False
    zh = language == "zh"
    saved = before - after
    if saved > 0:
        return ("一共省下了 " if zh else "You saved "), format_bytes(saved), True
    return ("共 " if zh else "Total size "), format_bytes(after), False


def retry_label(failed: int, language: str = "en") -> str:
    return f"重试失败的 {failed} 个" if language == "zh" else f"Retry {failed} failed"


def image_options_phrase(
    resize: str,
    quality: str,
    corners: str,
    target_kb: int,
    language: str = "en",
) -> str:
    """Describe batch image options that differ from the defaults; empty otherwise."""
    zh = language == "zh"
    if "custom" in {resize, quality, corners} or target_kb < 0:
        return "自定义选项" if zh else "custom options"
    phrases = {
        "resize": {
            "half": ("缩小到 50%", "resized to 50%"),
            "edge2048": ("缩小到 2048 像素", "resized to 2048 px"),
            "edge1080": ("缩小到 1080 像素", "resized to 1080 px"),
        },
        "quality": {
            "small": ("更小体积", "smaller files"),
            "best": ("最佳质量", "best quality"),
        },
        "corners": {
            "soft": ("24 像素圆角", "24 px corners"),
            "round": ("64 像素圆角", "64 px corners"),
        },
    }
    parts = [
        pair[0 if zh else 1]
        for field_name, value in (("resize", resize), ("quality", quality), ("corners", corners))
        if (pair := phrases[field_name].get(value))
    ]
    if target_kb > 0:
        parts.append(f"约 {target_kb} KB" if zh else f"about {target_kb} KB")
    return ("、" if zh else ", ").join(parts)


def short_duration(seconds: float | None) -> str:
    """"2:41" or "1:02:41" for card badges."""
    if seconds is None or not math.isfinite(seconds):
        return ""
    rounded = max(0, int(round(seconds)))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def result_size(job: JobRecord) -> str:
    if job.status == JobStatus.SUCCEEDED and job.output_size is not None:
        return format_bytes(job.output_size)
    return ""


def result_delta(job: JobRecord) -> str:
    """Signed size change, e.g. "−73%" or "+12%"; empty when unchanged."""
    if job.status != JobStatus.SUCCEEDED or job.output_size is None or not job.source.size:
        return ""
    change = round((job.output_size / job.source.size - 1) * 100)
    if change == 0:
        return ""
    return f"−{abs(change)}%" if change < 0 else f"+{change}%"
