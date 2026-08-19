from __future__ import annotations

import sys
import uuid
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from wemute.controller import JobController
from wemute.domain import (
    ConversionPlan,
    ImageOptions,
    JobRecord,
    JobStatus,
    MediaKind,
    OperationKind,
)
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


def test_per_file_image_settings_do_not_change_the_rest_of_the_batch(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (80, 60), "navy").save(first)
    Image.new("RGB", (80, 60), "gold").save(second)
    jobs = [
        JobRecord("first", probe_file(first, create_preview=False), "WebP"),
        JobRecord("second", probe_file(second, create_preview=False), "WebP"),
    ]
    controller = JobController(QueueModel(jobs), QueueStore(tmp_path / "queue.json"))

    controller.setJobImageResizePreset("first", "half")
    controller.setJobImageQualityPreset("first", "best")
    controller.setJobImageCornerPreset("first", "round")
    controller.setJobImageTargetSizeKb("first", 320)

    assert controller.imageResizePresetFor("first") == "half"
    assert controller.imageQualityPresetFor("first") == "best"
    assert controller.imageCornerPresetFor("first") == "round"
    assert controller.imageTargetSizeKbFor("first") == 320
    assert jobs[1].image_options == ImageOptions()
    assert controller.imageResizePreset == "custom"
    assert controller.imageTargetSizeKb == -1
    controller.shutdown()


def test_group_ai_action_keeps_per_file_conversion_override(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (32, 24), "navy").save(first)
    Image.new("RGB", (32, 24), "gold").save(second)
    jobs = [
        JobRecord("first", probe_file(first, create_preview=False), "WebP"),
        JobRecord("second", probe_file(second, create_preview=False), "JPEG"),
    ]
    model = QueueModel(jobs)
    controller = JobController(model, QueueStore(tmp_path / "queue.json"))
    model.set_enabled_ai_actions({OperationKind.REMOVE_BACKGROUND})

    controller.setGroupTargetFormat(MediaKind.IMAGE.value, "Remove Background")
    assert all(job.operation == OperationKind.REMOVE_BACKGROUND for job in jobs)
    assert all(job.target_format == "PNG" for job in jobs)

    controller.setTargetFormat("second", "JPEG")
    assert jobs[0].operation == OperationKind.REMOVE_BACKGROUND
    assert jobs[1].operation == OperationKind.CONVERT
    assert jobs[1].target_format == "JPEG"
    controller.shutdown()


def test_controller_reuses_one_ai_worker_for_a_batch(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    sources: list[Path] = []
    for index, color in enumerate(("navy", "gold")):
        source = tmp_path / f"source-{index}.png"
        Image.new("RGB", (32, 24), color).save(source)
        sources.append(source)
    jobs = [
        JobRecord(
            f"job-{index}",
            probe_file(source, create_preview=False),
            "PNG",
            operation=OperationKind.REMOVE_BACKGROUND,
        )
        for index, source in enumerate(sources)
    ]
    model = QueueModel(jobs)
    controller = JobController(model, QueueStore(tmp_path / "queue.json"))

    server = """
import json
import os
from pathlib import Path
import sys

for line in sys.stdin:
    request = json.loads(line)
    Path(request["destination"]).write_text(str(os.getpid()))
    event = {"job_id": request["job_id"], "type": "result", "ok": True}
    print("wemute_event=" + json.dumps(event, separators=(",", ":")), flush=True)
    """

    def fake_plan(job: JobRecord, destination: Path) -> ConversionPlan:
        destination.mkdir(parents=True, exist_ok=True)
        final = destination / f"{job.id}.txt"
        temporary = destination / f".{job.id}.tmp.txt"
        return ConversionPlan(
            job.id,
            Path(job.source.path),
            temporary,
            final,
            server_command=[sys.executable, "-u", "-c", server],
            worker_request={
                "job_id": job.id,
                "destination": str(temporary),
            },
        )

    controller.adapter.plan = fake_plan  # type: ignore[method-assign]
    controller._destination = str(tmp_path / "out")
    run_queue(controller)

    assert all(job.status == JobStatus.SUCCEEDED for job in jobs)
    worker_pids = {Path(job.output_path or "").read_text() for job in jobs}
    assert len(worker_pids) == 1
    assert controller._ai_process is not None
    controller.shutdown()
