from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from wemute.controller import JobController
from wemute.domain import JobRecord, JobStatus, MediaKind
from wemute.persistence import QueueStore
from wemute.probe import probe_file
from wemute.queue_model import QueueModel


def _app() -> None:
    QCoreApplication.instance() or QCoreApplication([])


def wait_until(predicate, timeout_ms: int = 10_000) -> None:  # noqa: ANN001
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: loop.quit() if predicate() else None)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    timer.start()
    deadline.start(timeout_ms)
    if not predicate():
        loop.exec()
    assert predicate(), "condition was not reached in time"


def test_parallel_jobs_never_share_an_output_name(tmp_path: Path) -> None:
    _app()
    sources = []
    for suffix in (".png", ".jpg", ".bmp"):
        path = tmp_path / f"photo{suffix}"
        Image.new("RGB", (40, 30), "teal").save(path)
        sources.append(path)
    jobs = [
        JobRecord(str(uuid.uuid4()), probe_file(path, create_preview=False), "WebP")
        for path in sources
    ]
    controller = JobController(QueueModel(jobs), QueueStore(tmp_path / "queue.json"))
    controller._destination = str(tmp_path / "out")
    controller.startAll()
    wait_until(lambda: not controller.busy)

    outputs = {job.output_path for job in jobs}
    assert all(job.status == JobStatus.SUCCEEDED for job in jobs)
    assert len(outputs) == 3
    assert controller.succeededCount == 3
    assert controller.notice and controller.noticeAction == "reveal"
    controller.shutdown()


def test_files_dropped_while_reading_are_not_lost(tmp_path: Path) -> None:
    _app()
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (20, 20), "red").save(first)
    Image.new("RGB", (20, 20), "blue").save(second)
    controller = JobController(QueueModel(), QueueStore(tmp_path / "queue.json"))

    controller.add_paths([str(first)])
    controller.add_paths([str(second)])
    wait_until(lambda: controller.fileCount == 2 and not controller.probing)
    controller.shutdown()


def test_unsupported_files_are_explained(tmp_path: Path) -> None:
    _app()
    unknown = tmp_path / "capture.bin"
    unknown.write_bytes(bytes(range(256)) * 4)
    image = tmp_path / "image.png"
    Image.new("RGB", (20, 20), "red").save(image)
    controller = JobController(QueueModel(), QueueStore(tmp_path / "queue.json"))

    controller.add_paths([str(unknown), str(image)])
    wait_until(lambda: not controller.probing and controller.fileCount == 1)
    assert "capture.bin" in controller.notice
    controller.shutdown()


def test_last_group_format_becomes_the_default_for_new_files(tmp_path: Path) -> None:
    _app()
    first = tmp_path / "first.png"
    later = tmp_path / "later.png"
    Image.new("RGB", (20, 20), "red").save(first)
    Image.new("RGB", (20, 20), "red").save(later)
    store = QueueStore(tmp_path / "queue.json")
    controller = JobController(QueueModel(), store)
    controller.add_paths([str(first)])
    wait_until(lambda: controller.fileCount == 1 and not controller.probing)
    controller.setGroupTargetFormat(MediaKind.IMAGE.value, "JPEG")
    controller.shutdown()

    fresh = JobController(QueueModel(), store)
    fresh.add_paths([str(later)])
    wait_until(lambda: fresh.fileCount == 1 and not fresh.probing)
    assert fresh.model.jobs[0].target_format == "JPEG"
    fresh.shutdown()


def test_remove_job_moves_selection_to_a_neighbour(tmp_path: Path) -> None:
    _app()
    paths = []
    for name in ("a.png", "b.png", "c.png"):
        path = tmp_path / name
        Image.new("RGB", (8, 8), "red").save(path)
        paths.append(path)
    jobs = [
        JobRecord(name, probe_file(path, create_preview=False), "WebP", selected=name == "b")
        for name, path in zip("abc", paths)
    ]
    controller = JobController(QueueModel(jobs), QueueStore(tmp_path / "queue.json"))
    controller.removeSelected()
    assert [job.id for job in controller.model.jobs] == ["a", "c"]
    assert controller.model.find("c").selected
    controller.shutdown()
