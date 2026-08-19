from pathlib import Path

from wemute.domain import FileDescriptor, JobRecord, MediaKind, OperationKind
from wemute.queue_model import QueueModel


def descriptor(path: Path, kind: MediaKind) -> FileDescriptor:
    return FileDescriptor(
        path=str(path),
        name=path.name,
        suffix=path.suffix,
        kind=kind,
    )


def test_model_groups_mixed_media_in_visual_order(tmp_path: Path) -> None:
    jobs = [
        JobRecord("v", descriptor(tmp_path / "clip.mov", MediaKind.VIDEO), "MP4 (H.264)"),
        JobRecord("i", descriptor(tmp_path / "image.png", MediaKind.IMAGE), "WebP"),
        JobRecord("a", descriptor(tmp_path / "sound.mp3", MediaKind.AUDIO), "WAV"),
    ]
    model = QueueModel(jobs)
    assert model.rowCount() == 6
    assert model.data(model.index(0), model.GroupLabelRole) == "Images"
    assert model.data(model.index(2), model.GroupLabelRole) == "Audio"
    assert model.data(model.index(4), model.GroupLabelRole) == "Video"


def test_group_header_exposes_shared_and_mixed_targets(tmp_path: Path) -> None:
    jobs = [
        JobRecord("one", descriptor(tmp_path / "one.jpg", MediaKind.IMAGE), "PNG"),
        JobRecord("two", descriptor(tmp_path / "two.jpg", MediaKind.IMAGE), "PNG"),
    ]
    model = QueueModel(jobs)
    header = model.index(0)
    assert model.data(header, model.GroupItemCountRole) == 2
    assert model.data(header, model.TargetFormatRole) == "PNG"
    jobs[1].target_format = "WebP"
    model.refresh()
    assert model.data(model.index(0), model.TargetFormatRole) == ""


def test_installed_ai_action_joins_the_existing_output_selector(tmp_path: Path) -> None:
    jobs = [JobRecord("one", descriptor(tmp_path / "one.jpg", MediaKind.IMAGE), "PNG")]
    model = QueueModel(jobs)
    model.set_enabled_ai_actions({OperationKind.REMOVE_BACKGROUND})

    options = model.data(model.index(0), model.TargetOptionsRole)
    assert "Remove Background" in options
