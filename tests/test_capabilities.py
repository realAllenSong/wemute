from pathlib import Path

from wemute.capabilities import apply_choice, default_target, options_for, unique_output_path
from wemute.domain import FileDescriptor, JobRecord, MediaKind, OperationKind


def test_default_targets_are_goal_oriented() -> None:
    assert default_target(MediaKind.IMAGE, ".png") == "WebP"
    assert default_target(MediaKind.AUDIO, ".mp3") == "WAV"
    assert {"HEIC", "AVIF"}.issubset(options_for(MediaKind.IMAGE))
    assert "MP4 (H.264)" in options_for(MediaKind.VIDEO)


def test_output_path_never_overwrites_source_or_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "portrait.png"
    source.write_bytes(b"source")
    first = unique_output_path(source, tmp_path, ".png")
    assert first.name == "portrait converted.png"
    first.write_bytes(b"existing")
    second = unique_output_path(source, tmp_path, ".png")
    assert second.name == "portrait converted 2.png"


def test_upscale_package_exposes_photo_and_illustration_scales() -> None:
    options = options_for(MediaKind.IMAGE, {OperationKind.UPSCALE})
    assert "Upscale Photo 2×" in options
    assert "Upscale Photo 4×" in options
    assert "Upscale Illustration 2×" in options
    assert "Upscale Illustration 4×" in options

    job = JobRecord(
        "image",
        FileDescriptor("/tmp/image.png", "image.png", ".png", MediaKind.IMAGE),
        "PNG",
    )
    assert apply_choice(job, "Upscale Illustration 4×")
    assert job.operation == OperationKind.UPSCALE
    assert job.operation_options == {"scale": 4, "style": "illustration"}
