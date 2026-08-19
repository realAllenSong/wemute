from pathlib import Path

from wemute.domain import (
    FileDescriptor,
    ImageOptions,
    JobRecord,
    JobStatus,
    MediaKind,
    OperationKind,
)
from wemute.persistence import QueueStore


def test_queue_round_trip_recovers_running_as_queued(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    source.write_bytes(b"data")
    job = JobRecord(
        id="job-1",
        source=FileDescriptor(
            path=str(source),
            name=source.name,
            suffix=".png",
            kind=MediaKind.IMAGE,
            size=4,
        ),
        target_format="WebP",
        status=JobStatus.RUNNING,
        progress=0.42,
        image_options=ImageOptions(
            scale_percent=50,
            quality=72,
            corner_radius=24,
            target_size_kb=512,
        ),
        operation=OperationKind.REMOVE_BACKGROUND,
    )
    store = QueueStore(tmp_path / "queue.json")
    store.save([job])
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].status == JobStatus.QUEUED
    assert loaded[0].source.path == str(source)
    assert loaded[0].image_options.scale_percent == 50
    assert loaded[0].image_options.quality == 72
    assert loaded[0].image_options.corner_radius == 24
    assert loaded[0].image_options.target_size_kb == 512
    assert loaded[0].operation == OperationKind.REMOVE_BACKGROUND


def test_missing_sources_are_not_restored(tmp_path: Path) -> None:
    missing = tmp_path / "gone.png"
    job = JobRecord(
        id="job-2",
        source=FileDescriptor(
            path=str(missing),
            name=missing.name,
            suffix=".png",
            kind=MediaKind.IMAGE,
        ),
        target_format="WebP",
    )
    store = QueueStore(tmp_path / "queue.json")
    store.save([job])
    assert store.load() == []
