from __future__ import annotations

import stat
import sys
import uuid
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

import doc_fixtures as fx
from wemute.components import ComponentManager, ComponentManifest
from wemute.components_qt import ComponentController
from wemute.controller import JobController
from wemute.domain import JobRecord, JobStatus
from wemute.persistence import QueueStore
from wemute.probe import probe_file
from wemute.queue_model import QueueModel

# Stands in for LibreOffice: writes "<stem>.<ext>" into --outdir.
FAKE_SOFFICE = f"""#!{sys.executable}
import sys
from pathlib import Path
args = sys.argv[1:]
outdir = Path(args[args.index("--outdir") + 1])
extension = args[args.index("--convert-to") + 1].split(":")[0]
source = Path(args[-1])
(outdir / f"{{source.stem}}.{{extension}}").write_bytes(b"%PDF-1.4\\n% fake office output\\n")
"""


def _app() -> None:
    QCoreApplication.instance() or QCoreApplication([])


def _wait(condition, timeout_ms: int = 10_000) -> bool:
    loop = QEventLoop()
    poll = QTimer()
    poll.timeout.connect(lambda: condition() and loop.quit())
    poll.start(20)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    poll.stop()
    return condition()


def _office_manifest() -> ComponentManifest:
    return ComponentManifest(
        id="libreoffice",
        name="LibreOffice",
        version="1",
        filename="lo.dmg",
        download_url="https://example.com/lo.dmg",
        sha256="1" * 64,
        size_bytes=300_000_000,
        license="MPL-2.0",
        license_url="https://example.com",
        archive_format="dmg",
        members=("LibreOffice.app",),
        executable="LibreOffice.app/Contents/MacOS/soffice",
    )


class _FakeOfficeManager(ComponentManager):
    def __init__(self, root: Path, fail: bool = False) -> None:
        super().__init__(root, [_office_manifest()])
        self.fail = fail
        self.installs = 0

    def install(self, manifest, progress=None, cancel=None, opener=None):  # noqa: ANN001
        self.installs += 1
        if progress:
            progress("download", manifest.size_bytes // 2, manifest.size_bytes)
        if self.fail:
            raise OSError("network is down")
        runtime = self.runtime_dir(manifest)
        executable = runtime / manifest.executable
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(FAKE_SOFFICE)
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        (runtime / ".wemute-component.json").write_text(f'{{"sha256": "{manifest.sha256}"}}')
        return executable


def _controller(tmp_path: Path, jobs: list[JobRecord], manager: ComponentManager | None = None) -> JobController:
    model = QueueModel(jobs)
    model.set_language("zh")
    components = ComponentController(manager or _FakeOfficeManager(tmp_path / "components"))
    controller = JobController(model, QueueStore(tmp_path / "queue.json"), components=components)
    controller._destination = str(tmp_path / "out")
    controller._preferences_path = tmp_path / "preferences.json"
    controller._preferences = {}
    return controller


def _job(path: Path, target: str) -> JobRecord:
    return JobRecord(str(uuid.uuid4()), probe_file(path, create_preview=False), target)


def _run(controller: JobController, timeout_ms: int = 20_000) -> None:
    controller.startAll()
    assert _wait(lambda: not controller.busy, timeout_ms), "batch timed out"


def test_sentence_names_document_families_and_offers_the_component_once(tmp_path: Path) -> None:
    _app()
    jobs = [_job(fx.make_docx(tmp_path / f"report {index}.docx"), "PDF") for index in range(3)]
    jobs.append(_job(fx.make_pptx(tmp_path / "deck.pptx"), "PDF"))
    controller = _controller(tmp_path, jobs)
    controller._refresh_summary()

    documents, slides = controller.groups
    assert (documents["lead"], documents["countLabel"], documents["verb"]) == ("把", "3 个 Word 文档", "转成")
    assert documents["targetLabel"] == "PDF"
    assert documents["component"] == "libreoffice"
    assert documents["componentState"] == "missing"
    assert documents["componentName"] == "文档组件"
    assert documents["componentSize"] == "300 MB"
    assert slides["component"] == ""
    labels = [entry.get("label") for entry in documents["entries"]]
    assert "打包成一个 ZIP" in labels and "打包成一个 7Z" in labels
    # A single file has nothing to combine.
    assert not any(entry.get("separator") for entry in slides["entries"])
    controller.shutdown()


def test_images_combine_into_one_pdf_in_list_order(tmp_path: Path) -> None:
    _app()
    colours = ["red", "green", "blue"]
    paths = []
    for index, colour in enumerate(colours):
        path = tmp_path / "trip" / f"{index}.png"
        path.parent.mkdir(exist_ok=True)
        Image.new("RGB", (120 + index * 10, 80), colour).save(path)
        paths.append(path)
    jobs = [_job(path, "WebP") for path in paths]
    controller = _controller(tmp_path, jobs)

    controller.setGroupTargetFormat("image", "One PDF")
    controller._refresh_summary()
    assert controller.groups[0]["verb"] == "合成"
    assert controller.groups[0]["targetLabel"] == "一个 PDF"
    _run(controller)

    assert all(job.status == JobStatus.SUCCEEDED for job in jobs)
    outputs = {job.output_path for job in jobs}
    assert len(outputs) == 1
    output = Path(outputs.pop())
    assert output.name == "trip.pdf"
    document = pdfium.PdfDocument(output)
    centres = []
    for index in range(len(document)):
        page = document[index].render(scale=0.2).to_pil().convert("RGB")
        centres.append(page.getpixel((page.width // 2, page.height // 2)))
    dominant = [max(range(3), key=lambda channel: pixel[channel]) for pixel in centres]
    assert dominant == [0, 1, 2]  # red, green, blue: list order
    # The batch total counts the one shared file once.
    assert controller.afterBytes == output.stat().st_size
    # A combined output is a choice for this batch, never the default for new files.
    assert "image" not in controller._preferences.get("formats", {})
    controller.shutdown()


def test_clear_and_undo_restore_the_exact_list(tmp_path: Path) -> None:
    _app()
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    Image.new("RGB", (20, 20), "red").save(first)
    Image.new("RGB", (20, 20), "blue").save(second)
    jobs = [_job(first, "WebP"), _job(second, "WebP")]
    controller = _controller(tmp_path, jobs)
    controller.setTargetFormat(jobs[1].id, "PNG")
    before = [(job.id, job.target_format) for job in controller.model.jobs]

    controller.clearWithUndo()
    assert controller.fileCount == 0
    assert controller.phase == "empty"
    assert controller.noticeAction == "undo"
    assert controller.notice == "已清空 2 个文件"

    controller.runNoticeAction()
    assert [(job.id, job.target_format) for job in controller.model.jobs] == before
    assert controller.notice == ""
    controller.shutdown()


def test_removing_a_kind_drops_its_line_and_can_be_undone(tmp_path: Path) -> None:
    _app()
    image = tmp_path / "a.png"
    Image.new("RGB", (20, 20), "red").save(image)
    jobs = [_job(image, "WebP"), _job(fx.make_markdown(tmp_path / "notes.md"), "HTML")]
    controller = _controller(tmp_path, jobs)

    controller.removeKind("data")
    controller._refresh_summary()
    assert [group["kind"] for group in controller.groups] == ["image"]
    assert controller.noticeAction == "undo"

    controller.undoClear()
    controller._refresh_summary()
    assert [group["kind"] for group in controller.groups] == ["image", "data"]
    controller.shutdown()


def test_start_downloads_a_missing_component_then_continues(tmp_path: Path) -> None:
    _app()
    manager = _FakeOfficeManager(tmp_path / "components")
    job = _job(fx.make_docx(tmp_path / "report.docx"), "PDF")
    controller = _controller(tmp_path, [job], manager)
    seen: list[tuple[str, bool, bool]] = []
    controller.model.dataChanged.connect(
        lambda *_: seen.append((job.stage, job.indeterminate, bool(job.waiting_component)))
    )

    _run(controller)

    assert manager.installs == 1
    assert job.status == JobStatus.SUCCEEDED, job.error
    assert Path(job.output_path).read_bytes().startswith(b"%PDF")
    assert any(waiting and stage.startswith("等待") for stage, _, waiting in seen)
    # The worker's stage lines reached the card, flagged as having no measurable progress.
    assert any(stage and indeterminate and not waiting for stage, indeterminate, waiting in seen)
    assert job.stage == "" and not job.waiting_component
    controller.shutdown()


def test_a_failed_component_download_fails_the_waiting_files(tmp_path: Path) -> None:
    _app()
    job = _job(fx.make_docx(tmp_path / "report.docx"), "PDF")
    controller = _controller(tmp_path, [job], _FakeOfficeManager(tmp_path / "components", fail=True))

    _run(controller)

    assert job.status == JobStatus.FAILED
    assert "文档组件下载失败" in (job.error or "")
    assert controller.phase == "done"
    controller.shutdown()


def test_overall_progress_counts_only_measured_progress(tmp_path: Path) -> None:
    _app()
    image = tmp_path / "a.png"
    Image.new("RGB", (20, 20), "red").save(image)
    done, running = _job(image, "WebP"), _job(image, "PNG")
    done.status = JobStatus.SUCCEEDED
    running.status = JobStatus.RUNNING
    running.progress = 0.5
    running.indeterminate = True
    controller = _controller(tmp_path, [done, running])
    controller._batch_job_ids = {done.id, running.id}

    assert controller.overallProgress == 0.5
    assert controller.anyIndeterminate
    running.indeterminate = False
    assert controller.overallProgress == 0.75
    controller.shutdown()
