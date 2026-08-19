from __future__ import annotations

import subprocess
import platform
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from wemute.domain import ConversionPlan, FileDescriptor, ImageOptions, JobRecord, MediaKind
from wemute.engine import FfmpegAdapter, finalize_output, remove_partial_output
from wemute.image_worker import convert_image
from wemute.paths import resolve_engine
from wemute.probe import probe_file


def make_job(source: Path, kind: MediaKind, target: str) -> JobRecord:
    descriptor = FileDescriptor(
        path=str(source),
        name=source.name,
        suffix=source.suffix,
        kind=kind,
        size=source.stat().st_size,
    )
    return JobRecord(str(uuid.uuid4()), descriptor, target)


def test_image_worker_applies_resize_quality_and_rounding(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (120, 80), (30, 120, 210)).save(source)
    adapter = FfmpegAdapter()
    job = make_job(source, MediaKind.IMAGE, "PNG")
    job.image_options = ImageOptions(scale_percent=50, quality=72, corner_radius=12)
    plan = adapter.plan(job, tmp_path / "out")
    subprocess.run(plan.command, capture_output=True, check=True)
    size = finalize_output(plan)
    assert size > 0
    assert plan.final_output.suffix == ".png"
    assert source.exists()
    with Image.open(plan.final_output) as converted:
        assert converted.size == (60, 40)
        assert converted.convert("RGBA").getpixel((0, 0))[3] == 0


def test_image_worker_targets_a_maximum_file_size(tmp_path: Path) -> None:
    source = tmp_path / "noise.png"
    Image.effect_noise((1000, 750), 96).convert("RGB").save(source)
    output = tmp_path / "target.jpg"

    convert_image(
        source,
        output,
        "JPEG",
        {"quality": 92, "target_size_kb": 48},
    )

    assert 0 < output.stat().st_size <= 48 * 1024
    with Image.open(output) as converted:
        assert converted.width > 16
        assert converted.height > 16


def test_multi_output_finalization_verifies_every_file_before_moving(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    vocals_temporary = tmp_path / ".vocals.wav"
    vocals_final = tmp_path / "Vocals.wav"
    instrumental_temporary = tmp_path / ".instrumental.wav"
    instrumental_final = tmp_path / "Instrumental.wav"
    vocals_temporary.write_bytes(b"vocals")
    plan = ConversionPlan(
        "job",
        source,
        vocals_temporary,
        vocals_final,
        additional_outputs=[(instrumental_temporary, instrumental_final)],
    )

    with pytest.raises(RuntimeError, match="instrumental"):
        finalize_output(plan)

    assert vocals_temporary.exists()
    assert not vocals_final.exists()

    instrumental_temporary.write_bytes(b"instrumental")
    assert finalize_output(plan) == len(b"vocals") + len(b"instrumental")
    assert vocals_final.read_bytes() == b"vocals"
    assert instrumental_final.read_bytes() == b"instrumental"


def test_multi_output_cleanup_removes_all_temporary_files(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    first = tmp_path / ".first.wav"
    second = tmp_path / ".second.wav"
    first.write_bytes(b"partial")
    second.write_bytes(b"partial")
    plan = ConversionPlan(
        "job",
        source,
        first,
        tmp_path / "first.wav",
        additional_outputs=[(second, tmp_path / "second.wav")],
    )

    remove_partial_output(plan)

    assert not first.exists()
    assert not second.exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="Uses the macOS ImageIO codec")
def test_native_heic_roundtrip_does_not_require_a_bundled_hevc_library(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    heic = tmp_path / "converted.heic"
    restored = tmp_path / "restored.png"
    Image.new("RGB", (64, 48), (24, 112, 220)).save(source)

    convert_image(source, heic, "HEIC", {"quality": 82})
    descriptor = probe_file(heic, create_preview=False)
    assert descriptor.width == 64
    assert descriptor.height == 48

    convert_image(heic, restored, "PNG")
    with Image.open(restored) as converted:
        assert converted.size == (64, 48)


def test_macos_video_profiles_do_not_require_gpl_encoders(tmp_path: Path) -> None:
    source = tmp_path / "source.mov"
    source.write_bytes(b"placeholder")
    adapter = FfmpegAdapter(executable=Path("/runtime/ffmpeg"))
    with patch("wemute.engine.platform.system", return_value="Darwin"):
        mkv = adapter._encoding_arguments(make_job(source, MediaKind.VIDEO, "MKV (H.264)"), "MKV (H.264)")
        prores = adapter._encoding_arguments(make_job(source, MediaKind.VIDEO, "MOV (ProRes)"), "MOV (ProRes)")
    assert "h264_videotoolbox" in mkv
    assert "prores_videotoolbox" in prores
    assert "libx264" not in mkv


@pytest.mark.skipif(resolve_engine("ffmpeg") is None, reason="FFmpeg is unavailable")
def test_mp3_to_wav_real_conversion(tmp_path: Path) -> None:
    ffmpeg = resolve_engine("ffmpeg")
    assert ffmpeg
    source = tmp_path / "tone.mp3"
    subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.3",
            "-c:a",
            "libmp3lame",
            "-y",
            str(source),
        ],
        capture_output=True,
        check=True,
    )
    descriptor = probe_file(source, create_preview=False)
    job = JobRecord(str(uuid.uuid4()), descriptor, "WAV")
    plan = FfmpegAdapter().plan(job, tmp_path / "out")
    subprocess.run(plan.command, capture_output=True, check=True)
    finalize_output(plan)
    converted = probe_file(plan.final_output, create_preview=False)
    assert converted.kind == MediaKind.AUDIO
    assert converted.duration is not None
    assert 0.2 <= converted.duration <= 0.5
