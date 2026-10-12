from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from wemute.controller import JobController
from wemute.domain import FileDescriptor, JobRecord, JobStatus, MediaKind
from wemute.i18n import TRANSLATIONS
from wemute.persistence import QueueStore
from wemute.presentation import count_phrase, done_title, savings_parts
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


def _job(job_id: str, kind: MediaKind, target: str, status: JobStatus = JobStatus.QUEUED) -> JobRecord:
    suffix = {MediaKind.IMAGE: ".png", MediaKind.VIDEO: ".mov", MediaKind.AUDIO: ".wav"}[kind]
    source = FileDescriptor(f"/tmp/{job_id}{suffix}", f"{job_id}{suffix}", suffix, kind, size=1000)
    return JobRecord(job_id, source, target, status=status)


def test_phase_moves_from_empty_to_done_and_back(tmp_path: Path) -> None:
    _app()
    paths = []
    for name in ("a.png", "b.png"):
        path = tmp_path / name
        Image.new("RGB", (40, 30), "teal").save(path)
        paths.append(path)
    controller = JobController(QueueModel(), QueueStore(tmp_path / "queue.json"))
    controller._destination = str(tmp_path / "out")
    phases: list[str] = []
    controller.phaseChanged.connect(lambda: phases.append(controller.phase))
    assert controller.phase == "empty"

    controller.add_paths([str(path) for path in paths])
    wait_until(lambda: controller.fileCount == 2 and not controller.probing)
    assert controller.phase == "ready"

    controller.startAll()
    wait_until(lambda: controller.phase == "done")
    assert "running" in phases
    assert controller.doneCount == 2
    assert controller.failedCount == 0
    assert controller.batchFinishedCount == controller.batchTotal == 2

    controller.newBatch()
    assert controller.phase == "empty"
    assert controller.fileCount == 0
    controller.shutdown()


def test_files_added_after_done_start_a_new_batch(tmp_path: Path) -> None:
    _app()
    first = tmp_path / "first.png"
    later = tmp_path / "later.png"
    Image.new("RGB", (20, 20), "red").save(first)
    Image.new("RGB", (20, 20), "blue").save(later)
    controller = JobController(QueueModel(), QueueStore(tmp_path / "queue.json"))
    controller._destination = str(tmp_path / "out")
    controller.add_paths([str(first)])
    wait_until(lambda: controller.fileCount == 1 and not controller.probing)
    controller.startAll()
    wait_until(lambda: controller.phase == "done")

    controller.add_paths([str(later)])
    wait_until(lambda: not controller.probing and controller.phase == "ready")
    assert [job.source.name for job in controller.model.jobs] == ["later.png"]
    controller.shutdown()


def test_stopped_batch_returns_to_ready(tmp_path: Path) -> None:
    _app()
    jobs = [
        _job("a", MediaKind.IMAGE, "WebP", JobStatus.SUCCEEDED),
        _job("b", MediaKind.IMAGE, "WebP", JobStatus.CANCELLED),
    ]
    controller = JobController(QueueModel(jobs), QueueStore(tmp_path / "queue.json"))
    assert controller.phase == "ready"
    controller.shutdown()


def test_groups_follow_sentence_order_with_counts(tmp_path: Path) -> None:
    _app()
    jobs = [
        _job("song", MediaKind.AUDIO, "FLAC"),
        _job("one", MediaKind.IMAGE, "WebP"),
        _job("clip", MediaKind.VIDEO, "MP4 (H.264)"),
        _job("two", MediaKind.IMAGE, "WebP"),
        _job("three", MediaKind.IMAGE, "JPEG"),
    ]
    model = QueueModel(jobs)
    model.set_language("zh")
    controller = JobController(model, QueueStore(tmp_path / "queue.json"))

    groups = controller.groups
    assert [group["kind"] for group in groups] == ["image", "video", "audio"]
    assert [group["count"] for group in groups] == [3, 1, 1]
    assert groups[0]["countLabel"] == "3 张图片"
    assert groups[0]["target"] == ""
    assert groups[2]["target"] == "FLAC"
    assert all(group["options"] for group in groups)

    controller.removeJob("song")
    assert [group["kind"] for group in controller.groups] == ["image", "video"]
    controller.shutdown()


def test_sentence_phrases_read_naturally() -> None:
    assert count_phrase(MediaKind.IMAGE, 12, "zh") == "12 张图片"
    assert count_phrase(MediaKind.VIDEO, 2, "zh") == "2 个视频"
    assert count_phrase(MediaKind.AUDIO, 1, "en") == "1 audio file"
    assert count_phrase(MediaKind.IMAGE, 1, "en") == "1 image"
    assert done_title(14, 0, "zh") == "14 个文件都转好了"
    assert done_title(12, 2, "zh") == "12 个已完成，2 个失败"
    lead, amount, saved = savings_parts(200_000_000, 56_000_000, "zh")
    assert (lead, amount, saved) == ("一共省下了 ", "144.0 MB", True)
    assert savings_parts(1000, 2000, "en")[2] is False


def test_both_languages_define_the_same_keys() -> None:
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["zh"])
