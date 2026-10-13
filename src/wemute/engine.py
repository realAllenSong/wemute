from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from collections.abc import Callable

from wemute.capabilities import is_combine, release_output, target_definition, unique_output_path
from wemute.domain import MEDIA_KINDS, ConversionPlan, JobRecord, MediaKind, OperationKind
from wemute.ai_engine import AIEngineAdapter
from wemute.paths import CACHE_ROOT, resolve_engine


class EngineUnavailableError(RuntimeError):
    pass


class FfmpegAdapter:
    def __init__(
        self,
        executable: Path | None = None,
        ai_adapter: AIEngineAdapter | None = None,
    ) -> None:
        self.executable = executable or resolve_engine("ffmpeg")
        self.ai_adapter = ai_adapter or AIEngineAdapter()
        # Set by the controller: installed component tools and the UI language.
        self.tools: Callable[[], dict[str, str]] = dict
        self.language = "en"

    @property
    def available(self) -> bool:
        # Image conversions use the bundled Python/Pillow worker and remain
        # available even when FFmpeg is not installed.
        return True

    def plan(
        self,
        job: JobRecord,
        destination: Path,
        members: list[JobRecord] | None = None,
    ) -> ConversionPlan:
        if job.operation != OperationKind.CONVERT:
            return self.ai_adapter.plan(job, destination)
        if job.source.kind not in MEDIA_KINDS or is_combine(job.target_format):
            from wemute.engines import plan_file_job

            return plan_file_job(
                job,
                destination,
                members=members,
                tools=self.tools(),
                language=self.language,
                office_profile=CACHE_ROOT / "libreoffice-profile",
                calibre_config=CACHE_ROOT / "calibre-config",
            )
        definition = target_definition(job.target_format)
        destination.mkdir(parents=True, exist_ok=True)
        source = Path(job.source.path)
        final = unique_output_path(source, destination, definition.extension)
        temporary = final.with_name(f".{final.stem}.wemute-{job.id[:8]}{final.suffix}")
        if job.source.kind == MediaKind.IMAGE:
            if getattr(sys, "frozen", False):
                command = [
                    sys.executable,
                    "--image-worker",
                    str(source),
                    str(temporary),
                    definition.label,
                    json.dumps(asdict(job.image_options), separators=(",", ":")),
                ]
            else:
                command = [
                    sys.executable,
                    "-m",
                    "wemute.image_worker",
                    str(source),
                    str(temporary),
                    definition.label,
                    json.dumps(asdict(job.image_options), separators=(",", ":")),
                ]
            return ConversionPlan(job.id, source, temporary, final, command)

        if not self.executable:
            raise EngineUnavailableError("FFmpeg is not available for audio and video conversion.")
        command = [
            str(self.executable),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(source),
        ]
        command.extend(self._encoding_arguments(job, definition.label))
        command.extend(["-map_metadata", "0", "-progress", "pipe:1", "-nostats", str(temporary)])
        return ConversionPlan(job.id, source, temporary, final, command)

    def _encoding_arguments(self, job: JobRecord, label: str) -> list[str]:
        if job.source.kind == MediaKind.AUDIO:
            common = ["-vn"]
            if label == "MP3":
                return common + ["-c:a", "libmp3lame", "-q:a", "2"]
            if label == "WAV":
                return common + ["-c:a", "pcm_s24le"]
            if label == "FLAC":
                return common + ["-c:a", "flac", "-compression_level", "8"]
            if label == "M4A (AAC)":
                return common + ["-c:a", "aac", "-b:a", "256k"]
            if label == "AIFF":
                return common + ["-c:a", "pcm_s24be"]
            if label == "OGG":
                return common + ["-c:a", "vorbis", "-strict", "-2", "-q:a", "6"]
            return common + ["-c:a", "libopus", "-b:a", "160k"]

        if job.source.kind == MediaKind.VIDEO:
            is_macos = platform.system() == "Darwin"
            # Apple Silicon VideoToolbox supports constant-quality encoding, which
            # sizes output to the content instead of inflating small clips.
            constant_quality = is_macos and platform.machine() == "arm64"
            if label == "MP4 (H.264)":
                codec = "h264_videotoolbox" if is_macos else "libx264"
                args = ["-c:v", codec]
                if constant_quality:
                    args += ["-q:v", "60"]
                else:
                    args += ["-b:v", "8M"] if is_macos else ["-crf", "20", "-preset", "medium"]
                return args + ["-tag:v", "avc1", "-c:a", "aac", "-b:a", "192k"]
            if label == "MP4 (H.265)":
                codec = "hevc_videotoolbox" if is_macos else "libx265"
                args = ["-c:v", codec]
                if constant_quality:
                    args += ["-q:v", "55"]
                else:
                    args += ["-b:v", "6M"] if is_macos else ["-crf", "24", "-preset", "medium"]
                return args + ["-tag:v", "hvc1", "-c:a", "aac", "-b:a", "192k"]
            if label == "MOV (ProRes)":
                codec = "prores_videotoolbox" if is_macos else "prores_ks"
                return ["-c:v", codec, "-profile:v", "3", "-c:a", "pcm_s24le"]
            if label == "MKV (H.264)":
                if is_macos:
                    quality = ["-q:v", "60"] if constant_quality else ["-b:v", "8M"]
                    return ["-c:v", "h264_videotoolbox", *quality, "-c:a", "aac"]
                return ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-c:a", "aac"]
            if label == "WebM (VP9)":
                return ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus"]
            return [
                "-vf",
                "fps=15,scale='min(1280,iw)':-2:flags=lanczos",
                "-loop",
                "0",
            ]
        raise ValueError(f"Unsupported media kind: {job.source.kind}")


_RENAME_EXCL = 0x00000004


def _rename_exclusive(source: Path, target: Path) -> bool:
    """Rename without ever replacing an existing file or folder. False if taken."""
    if sys.platform == "darwin":
        import ctypes
        import errno

        libc = ctypes.CDLL(None, use_errno=True)
        result = libc.renamex_np(
            os.fsencode(source), os.fsencode(target), ctypes.c_uint(_RENAME_EXCL)
        )
        if result == 0:
            return True
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            return False
        if code not in {errno.ENOTSUP, errno.EINVAL, errno.ENOSYS}:
            raise OSError(code, os.strerror(code), str(target))
    if target.exists() or target.is_symlink():
        return False
    os.rename(source, target)
    return True


def _place(temporary: Path, final: Path) -> Path:
    """Move a finished output into place, numbering the name if it was taken meanwhile."""
    candidate = final
    stem, suffix = (final.name, "") if temporary.is_dir() else (final.stem, final.suffix)
    number = 2
    while not _rename_exclusive(temporary, candidate):
        candidate = final.with_name(f"{stem} {number}{suffix}")
        number += 1
    return candidate


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def finalize_output(plan: ConversionPlan) -> int:
    outputs = [(plan.temporary_output, plan.final_output), *plan.additional_outputs]
    missing = [temporary.name for temporary, _final in outputs if not temporary.exists()]
    if missing:
        for _temporary, final in outputs:
            release_output(final)
        raise RuntimeError(
            "The converter did not produce all output files: " + ", ".join(missing)
        )
    total_size = 0
    placed_outputs: list[tuple[Path, Path]] = []
    for temporary, final in outputs:
        target = final
        if temporary.is_dir() and not plan.folder_output and final.suffix:
            # A converter may answer with a folder (e.g. one CSV per sheet).
            target = final.with_name(final.stem)
        placed = _place(temporary, target)
        release_output(final)
        if placed.is_file():
            try:
                shutil.copystat(plan.source, placed)
            except OSError:
                pass
        total_size += _tree_size(placed)
        placed_outputs.append((temporary, placed))
    plan.final_output = placed_outputs[0][1]
    plan.additional_outputs = placed_outputs[1:]
    return total_size


def remove_partial_output(plan: ConversionPlan | None) -> None:
    if not plan:
        return
    for temporary, final in [
        (plan.temporary_output, plan.final_output),
        *plan.additional_outputs,
    ]:
        release_output(final)
        try:
            if temporary.is_dir() and not temporary.is_symlink():
                shutil.rmtree(temporary, ignore_errors=True)
            else:
                temporary.unlink(missing_ok=True)
        except OSError:
            pass
