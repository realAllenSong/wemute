from __future__ import annotations

import concurrent.futures
import os
import time
import uuid
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QProcess,
    QSettings,
    QTimer,
    QUrl,
    QObject,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication

from wemute.capabilities import apply_choice, default_target, is_choice_compatible
from wemute.domain import ConversionPlan, FileDescriptor, JobRecord, JobStatus, MediaKind
from wemute.ai_engine import AIEngineAdapter
from wemute.engine import FfmpegAdapter, finalize_output, remove_partial_output
from wemute.model_packages import ModelPackageManager
from wemute.persistence import QueueStore
from wemute.paths import CACHE_ROOT
from wemute.probe import expand_paths, probe_file
from wemute.queue_model import QueueModel


class JobController(QObject):
    fileCountChanged = Signal()
    busyChanged = Signal()
    probingChanged = Signal()
    destinationChanged = Signal()
    errorChanged = Signal()
    imageSettingsChanged = Signal()
    _probeReady = Signal(object, str)

    def __init__(
        self,
        model: QueueModel,
        store: QueueStore | None = None,
        packages: ModelPackageManager | None = None,
    ) -> None:
        super().__init__()
        self.model = model
        self.store = store or QueueStore()
        self.packages = packages or ModelPackageManager()
        self.ai_adapter = AIEngineAdapter(self.packages)
        self.adapter = FfmpegAdapter(ai_adapter=self.ai_adapter)
        self.model.set_enabled_ai_actions(self.ai_adapter.enabled_actions())
        self.settings = QSettings("Wemute", "Wemute")
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self._probing = False
        self._busy = False
        self._last_error = ""
        self._destination = str(self.settings.value("destination", ""))
        self._process: QProcess | None = None
        self._active_job: JobRecord | None = None
        self._active_plan: ConversionPlan | None = None
        self._stderr = bytearray()
        self._stdout_buffer = ""
        self._cancel_requested = False
        self._pause_after_current = False
        self._probeReady.connect(self._on_probe_ready)

    @Property(int, notify=fileCountChanged)
    def fileCount(self) -> int:
        return len(self.model.jobs)

    @Property(bool, notify=fileCountChanged)
    def hasJobs(self) -> bool:
        return bool(self.model.jobs)

    @Property(int, notify=fileCountChanged)
    def groupCount(self) -> int:
        return len({job.source.kind for job in self.model.jobs})

    @Property(bool, notify=fileCountChanged)
    def hasImageJobs(self) -> bool:
        return any(job.source.kind == MediaKind.IMAGE for job in self.model.jobs)

    @Property(str, notify=imageSettingsChanged)
    def imageResizePreset(self) -> str:
        values = {
            (job.image_options.scale_percent, job.image_options.max_edge)
            for job in self._image_jobs()
        }
        if len(values) != 1:
            return "custom"
        value = next(iter(values))
        return {
            (100, None): "original",
            (50, None): "half",
            (100, 2048): "edge2048",
            (100, 1080): "edge1080",
        }.get(value, "custom")

    @Property(str, notify=imageSettingsChanged)
    def imageQualityPreset(self) -> str:
        values = {job.image_options.quality for job in self._image_jobs()}
        if len(values) != 1:
            return "custom"
        return {72: "small", 84: "balanced", 92: "best"}.get(next(iter(values)), "custom")

    @Property(str, notify=imageSettingsChanged)
    def imageCornerPreset(self) -> str:
        values = {job.image_options.corner_radius for job in self._image_jobs()}
        if len(values) != 1:
            return "custom"
        return {0: "none", 24: "soft", 64: "round"}.get(next(iter(values)), "custom")

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=probingChanged)
    def probing(self) -> bool:
        return self._probing

    @Property(bool, constant=True)
    def engineAvailable(self) -> bool:
        return self.adapter.available

    @Property(str, notify=destinationChanged)
    def destinationLabel(self) -> str:
        return Path(self._destination).name if self._destination else "Same Folder"

    @Property(str, notify=errorChanged)
    def lastError(self) -> str:
        return self._last_error

    def restore(self) -> None:
        self.model.replace(self.store.load())
        if self.model.jobs and not any(job.selected for job in self.model.jobs):
            self.model.jobs[0].selected = True
            self.model.refresh()
        self.fileCountChanged.emit()
        self.imageSettingsChanged.emit()

    def shutdown(self) -> None:
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.kill()
            self._process.waitForFinished(1000)
        self.store.save(self.model.jobs)
        self._executor.shutdown(wait=False, cancel_futures=True)

    @Slot("QVariantList")
    def addUrls(self, urls: list[object]) -> None:
        paths: list[str] = []
        for value in urls:
            if isinstance(value, QUrl):
                local = value.toLocalFile()
            else:
                candidate = QUrl(str(value))
                local = candidate.toLocalFile() or str(value)
            if local:
                paths.append(local)
        self.add_paths(paths)

    def add_paths(self, paths: list[str]) -> None:
        if not paths or self._probing:
            return
        self._probing = True
        self.probingChanged.emit()
        existing = {job.source.path for job in self.model.jobs}

        def work() -> tuple[list[FileDescriptor], str]:
            descriptors: list[FileDescriptor] = []
            errors: list[str] = []
            for path in expand_paths(paths):
                if str(path) in existing:
                    continue
                try:
                    descriptors.append(probe_file(path))
                except Exception as exc:  # Defensive isolation: one bad file must not block the batch.
                    errors.append(f"{path.name}: {exc}")
            return descriptors, "\n".join(errors)

        future = self._executor.submit(work)

        def completed(result: concurrent.futures.Future[tuple[list[FileDescriptor], str]]) -> None:
            try:
                descriptors, error = result.result()
            except Exception as exc:  # pragma: no cover - executor-level failure
                descriptors, error = [], str(exc)
            self._probeReady.emit(descriptors, error)

        future.add_done_callback(completed)

    @Slot(object, str)
    def _on_probe_ready(self, descriptors: list[FileDescriptor], error: str) -> None:
        now = time.time()
        additions: list[JobRecord] = []
        for index, descriptor in enumerate(descriptors):
            target = default_target(descriptor.kind, descriptor.suffix)
            if not target:
                continue
            additions.append(
                JobRecord(
                    id=str(uuid.uuid4()),
                    source=descriptor,
                    target_format=target,
                    created_at=now + index / 1000,
                    selected=not self.model.jobs and index == 0,
                )
            )
        self.model.replace([*self.model.jobs, *additions])
        self._probing = False
        self._set_error(error)
        self._persist()
        self.fileCountChanged.emit()
        self.probingChanged.emit()
        self.imageSettingsChanged.emit()

    @staticmethod
    def _reset_job(job: JobRecord) -> None:
        if job.status == JobStatus.RUNNING:
            return
        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            job.status = JobStatus.QUEUED
            job.progress = 0.0
            job.output_path = None
            job.output_size = None
            job.error = None

    @Slot(str, str)
    def setTargetFormat(self, job_id: str, target: str) -> None:
        job = self.model.find(job_id)
        if not job or not is_choice_compatible(
            job.source.kind, target, self.model.enabled_ai_actions
        ):
            return
        previous = (job.operation, job.target_format, dict(job.operation_options))
        if not apply_choice(job, target):
            return
        if previous == (job.operation, job.target_format, job.operation_options):
            return
        self._reset_job(job)
        self.model.refresh()
        self._persist()

    @Slot(str, str)
    def setGroupTargetFormat(self, kind_value: str, target: str) -> None:
        try:
            kind = MediaKind(kind_value)
        except ValueError:
            return
        if not is_choice_compatible(kind, target, self.model.enabled_ai_actions):
            return
        changed = False
        for job in self.model.jobs:
            if job.source.kind != kind or job.status == JobStatus.RUNNING:
                continue
            previous = (job.operation, job.target_format, dict(job.operation_options))
            if not apply_choice(job, target):
                continue
            if previous == (job.operation, job.target_format, job.operation_options):
                continue
            self._reset_job(job)
            changed = True
        if changed:
            self.model.refresh()
            self._persist()

    @Slot(str)
    def setImageResizePreset(self, preset: str) -> None:
        values = {
            "original": (100, None),
            "half": (50, None),
            "edge2048": (100, 2048),
            "edge1080": (100, 1080),
        }
        if preset not in values:
            return
        scale, max_edge = values[preset]
        for job in self._image_jobs():
            if job.status == JobStatus.RUNNING:
                continue
            job.image_options.scale_percent = scale
            job.image_options.max_edge = max_edge
            self._reset_job(job)
        self._finish_image_settings_change()

    @Slot(str)
    def setImageQualityPreset(self, preset: str) -> None:
        values = {"small": 72, "balanced": 84, "best": 92}
        if preset not in values:
            return
        for job in self._image_jobs():
            if job.status == JobStatus.RUNNING:
                continue
            job.image_options.quality = values[preset]
            self._reset_job(job)
        self._finish_image_settings_change()

    @Slot(str)
    def setImageCornerPreset(self, preset: str) -> None:
        values = {"none": 0, "soft": 24, "round": 64}
        if preset not in values:
            return
        for job in self._image_jobs():
            if job.status == JobStatus.RUNNING:
                continue
            job.image_options.corner_radius = values[preset]
            self._reset_job(job)
        self._finish_image_settings_change()

    def _image_jobs(self) -> list[JobRecord]:
        return [job for job in self.model.jobs if job.source.kind == MediaKind.IMAGE]

    def _finish_image_settings_change(self) -> None:
        self.model.refresh()
        self._persist()
        self.imageSettingsChanged.emit()

    @Slot(str)
    def selectJob(self, job_id: str) -> None:
        for job in self.model.jobs:
            job.selected = job.id == job_id
        self.model.refresh()

    @Slot(str)
    def removeJob(self, job_id: str) -> None:
        if self._active_job and self._active_job.id == job_id:
            self.cancelJob(job_id)
            return
        self.model.replace(job for job in self.model.jobs if job.id != job_id)
        self._persist()
        self.fileCountChanged.emit()
        self.imageSettingsChanged.emit()

    @Slot()
    def clearCompleted(self) -> None:
        self.model.replace(job for job in self.model.jobs if job.status != JobStatus.SUCCEEDED)
        self._persist()
        self.fileCountChanged.emit()
        self.imageSettingsChanged.emit()

    @Slot()
    def clearAll(self) -> None:
        if self._busy and self._active_job:
            self.cancelJob(self._active_job.id)
        self.model.replace([])
        self._persist()
        self.fileCountChanged.emit()
        self.imageSettingsChanged.emit()

    @Slot()
    def retryFailed(self) -> None:
        for job in self.model.jobs:
            if job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
                job.status = JobStatus.QUEUED
                job.progress = 0.0
                job.error = None
        self.model.refresh()
        self._persist()

    @Slot(str)
    def setDestination(self, url: str) -> None:
        value = QUrl(url)
        local = value.toLocalFile() or url
        self._destination = str(Path(local).expanduser()) if local else ""
        self.settings.setValue("destination", self._destination)
        self.destinationChanged.emit()

    @Slot()
    def resetDestination(self) -> None:
        self._destination = ""
        self.settings.remove("destination")
        self.destinationChanged.emit()

    @Slot()
    def startAll(self) -> None:
        if self._busy or not self.model.jobs:
            return
        if not self.adapter.available:
            self._set_error("FFmpeg is not available. Install it or set WEMUTE_FFMPEG.")
            return
        for job in self.model.jobs:
            if job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
                job.status = JobStatus.QUEUED
                job.progress = 0.0
                job.error = None
        self._busy = True
        self.busyChanged.emit()
        self.model.refresh()
        self._run_next()

    def _run_next(self) -> None:
        if self._pause_after_current:
            self._pause_after_current = False
            self._busy = False
            self._active_job = None
            self._active_plan = None
            self.busyChanged.emit()
            self._persist()
            return
        job = next((item for item in self.model.jobs if item.status == JobStatus.QUEUED), None)
        if not job:
            self._busy = False
            self._active_job = None
            self._active_plan = None
            self.busyChanged.emit()
            self._persist()
            return
        source = Path(job.source.path)
        destination = Path(self._destination) if self._destination else source.parent
        try:
            plan = self.adapter.plan(job, destination)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            self.model.refresh()
            QTimer.singleShot(0, self._run_next)
            return

        job.status = JobStatus.RUNNING
        job.progress = 0.01
        job.error = None
        self._active_job = job
        self._active_plan = plan
        self._stderr.clear()
        self._stdout_buffer = ""
        self._cancel_requested = False
        self.model.refresh()
        self._persist()

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_progress)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        self._process = process
        process.start(plan.command[0], plan.command[1:])

    @Slot()
    def _read_progress(self) -> None:
        if not self._process or not self._active_job:
            return
        self._stdout_buffer += bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        lines = self._stdout_buffer.split("\n")
        self._stdout_buffer = lines.pop()
        duration = self._active_job.source.duration or 0
        changed = False
        for line in lines:
            key, _, raw = line.partition("=")
            if key == "wemute_progress":
                try:
                    self._active_job.progress = max(
                        self._active_job.progress, min(0.99, float(raw))
                    )
                    changed = True
                except ValueError:
                    continue
            elif key in {"out_time_us", "out_time_ms"} and duration:
                try:
                    micros = int(raw)
                    self._active_job.progress = max(
                        self._active_job.progress, min(0.99, micros / (duration * 1_000_000))
                    )
                    changed = True
                except ValueError:
                    continue
            elif key == "progress" and raw == "end":
                self._active_job.progress = 0.99
                changed = True
        if changed:
            self.model.refresh()

    @Slot()
    def _read_stderr(self) -> None:
        if self._process:
            self._stderr.extend(bytes(self._process.readAllStandardError()))

    @Slot(int, QProcess.ExitStatus)
    def _process_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        job = self._active_job
        plan = self._active_plan
        process = self._process
        self._process = None
        if process:
            process.deleteLater()
        if not job or not plan:
            return
        if self._cancel_requested or job.status == JobStatus.CANCELLED:
            remove_partial_output(plan)
            job.status = JobStatus.CANCELLED
            job.progress = 0.0
        elif exit_code == 0:
            try:
                job.output_size = finalize_output(plan)
                job.output_path = str(plan.final_output)
                job.status = JobStatus.SUCCEEDED
                job.progress = 1.0
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                remove_partial_output(plan)
        else:
            message = self._stderr.decode("utf-8", errors="replace").strip()
            job.status = JobStatus.FAILED
            job.error = message.splitlines()[-1] if message else f"FFmpeg exited with code {exit_code}."
            job.progress = 0.0
            remove_partial_output(plan)
        self._active_job = None
        self._active_plan = None
        self.model.refresh()
        self._persist()
        QTimer.singleShot(0, self._run_next)

    @Slot(QProcess.ProcessError)
    def _process_error(self, _error: QProcess.ProcessError) -> None:
        if self._process:
            self._stderr.extend(self._process.errorString().encode("utf-8"))

    @Slot(str)
    def cancelJob(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if not job:
            return
        if self._active_job and self._active_job.id == job_id and self._process:
            self._cancel_requested = True
            job.status = JobStatus.CANCELLED
            self._process.terminate()
            process = self._process
            QTimer.singleShot(
                1200,
                lambda: process.kill() if process.state() != QProcess.NotRunning else None,
            )
        elif job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
        self.model.refresh()
        self._persist()

    @Slot()
    def cancelCurrent(self) -> None:
        if self._active_job:
            self.cancelJob(self._active_job.id)

    @Slot()
    def cancelAll(self) -> None:
        for job in self.model.jobs:
            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
        if self._active_job:
            self.cancelJob(self._active_job.id)
        else:
            self._busy = False
            self.busyChanged.emit()
        self.model.refresh()
        self._persist()

    @Slot()
    def pauseAfterCurrent(self) -> None:
        if self._busy:
            self._pause_after_current = True

    @Slot(str)
    def revealJob(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if not job:
            return
        path = Path(job.output_path) if job.output_path else Path(job.source.path)
        target = path.parent if path.is_file() else path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    @Slot()
    def pasteFiles(self) -> None:
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        urls = [url for url in mime.urls() if url.isLocalFile()]
        if urls:
            self.addUrls(urls)
            return
        image = clipboard.image()
        if image.isNull():
            return
        imports = CACHE_ROOT / "imports"
        imports.mkdir(parents=True, exist_ok=True)
        target = imports / f"Pasted Image {int(time.time())}.png"
        if image.save(str(target), "PNG"):
            self.add_paths([str(target)])

    @Slot()
    def quickLookSelected(self) -> None:
        job = next((item for item in self.model.jobs if item.selected), None)
        if not job:
            return
        source = Path(job.source.path)
        if os.name == "posix" and Path("/usr/bin/qlmanage").exists():
            QProcess.startDetached("/usr/bin/qlmanage", ["-p", str(source)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(source)))

    def seed_demo(self, descriptors: list[FileDescriptor]) -> None:
        targets = ["WebP", "FLAC", "MP4 (H.265)", "MP4 (H.265)", "MP4 (H.265)"]
        statuses = [
            JobStatus.SUCCEEDED,
            JobStatus.RUNNING,
            JobStatus.SUCCEEDED,
            JobStatus.QUEUED,
            JobStatus.QUEUED,
        ]
        jobs: list[JobRecord] = []
        for index, descriptor in enumerate(descriptors[:5]):
            job = JobRecord(
                id=f"demo-{index}",
                source=descriptor,
                target_format=targets[index],
                status=statuses[index],
                progress=0.48 if index == 1 else (1.0 if statuses[index] == JobStatus.SUCCEEDED else 0.0),
                output_size=int(descriptor.size * 0.39) if statuses[index] == JobStatus.SUCCEEDED else None,
                selected=index == 3,
            )
            jobs.append(job)
        self.model.replace(jobs)
        self.fileCountChanged.emit()

    def _persist(self) -> None:
        self.store.save(self.model.jobs)

    def _set_error(self, message: str) -> None:
        self._last_error = message
        self.errorChanged.emit()
