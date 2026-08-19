from __future__ import annotations

import time
import uuid
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from wemute.controller import JobController
from wemute.domain import JobRecord, JobStatus, MediaKind
from wemute.persistence import QueueStore
from wemute.probe import probe_file
from wemute.queue_model import QueueModel


def run_queue(controller: JobController, timeout_ms: int = 8_000) -> None:
    loop = QEventLoop()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)

    def state_changed() -> None:
        if not controller.busy:
            loop.quit()

    controller.busyChanged.connect(state_changed)
    timeout.start(timeout_ms)
    controller.startAll()
    if controller.busy:
        loop.exec()
    assert not timeout.isActive() or not controller.busy, "conversion queue timed out"


def test_bad_file_fails_without_blocking_the_next_job(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not-an-image")
    valid = tmp_path / "valid.png"
    Image.new("RGB", (64, 48), (80, 130, 190)).save(valid)

    jobs = [
        JobRecord(str(uuid.uuid4()), probe_file(broken, create_preview=False), "WebP"),
        JobRecord(str(uuid.uuid4()), probe_file(valid, create_preview=False), "WebP"),
    ]
    model = QueueModel(jobs)
    controller = JobController(model, QueueStore(tmp_path / "queue.json"))
    controller._destination = str(tmp_path / "out")
    run_queue(controller)

    assert jobs[0].status == JobStatus.FAILED
    assert jobs[1].status == JobStatus.SUCCEEDED
    assert jobs[1].output_path
    assert Path(jobs[1].output_path).exists()
    controller.shutdown()


def test_group_target_and_image_presets_apply_in_one_action(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (80, 60), "navy").save(first)
    Image.new("RGB", (80, 60), "gold").save(second)
    jobs = [
        JobRecord("first", probe_file(first, create_preview=False), "WebP"),
        JobRecord(
            "second",
            probe_file(second, create_preview=False),
            "JPEG",
            status=JobStatus.SUCCEEDED,
            progress=1.0,
        ),
    ]
    model = QueueModel(jobs)
    controller = JobController(model, QueueStore(tmp_path / "queue.json"))

    controller.setGroupTargetFormat(MediaKind.IMAGE.value, "PNG")
    controller.setImageResizePreset("half")
    controller.setImageQualityPreset("small")
    controller.setImageCornerPreset("soft")

    assert {job.target_format for job in jobs} == {"PNG"}
    assert all(job.status == JobStatus.QUEUED for job in jobs)
    assert all(job.image_options.scale_percent == 50 for job in jobs)
    assert all(job.image_options.quality == 72 for job in jobs)
    assert all(job.image_options.corner_radius == 24 for job in jobs)
    controller.shutdown()
