from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
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

from wemute.capabilities import (
    ACTION_BY_LABEL,
    ACTIONS,
    apply_choice,
    default_target,
    is_choice_compatible,
    is_compatible,
    target_definition,
)
from wemute.domain import (
    ConversionPlan,
    FileDescriptor,
    JobRecord,
    JobStatus,
    MediaKind,
    OperationKind,
)
from wemute.ai_engine import AIEngineAdapter
from wemute.engine import FfmpegAdapter, finalize_output, remove_partial_output
from wemute.model_packages import ModelPackageManager
from wemute.persistence import QueueStore
from wemute.paths import CACHE_ROOT
from wemute.presentation import batch_notice, intake_notice, progress_summary
from wemute.probe import expand_paths, media_kind_for, probe_file
from wemute.queue_model import QueueModel


def _lane_limits() -> dict[str, int]:
    cores = os.cpu_count() or 4
    return {
        # Pillow work is single-threaded per process, so images scale with cores.
        "image": max(2, min(6, cores // 2)),
        "audio": 2,
        # FFmpeg and VideoToolbox already saturate the machine for one video.
        "video": 1,
        # AI jobs share one long-lived worker process.
        "ai": 1,
    }


@dataclass(eq=False)
class _Run:
    job: JobRecord
    plan: ConversionPlan
    lane: str
    process: QProcess | None = None
    stderr: bytearray = field(default_factory=bytearray)
    stdout: str = ""
    cancel_requested: bool = False


class JobController(QObject):
    fileCountChanged = Signal()
    busyChanged = Signal()
    probingChanged = Signal()
    destinationChanged = Signal()
    errorChanged = Signal()
    imageSettingsChanged = Signal()
    queueStateChanged = Signal()
    noticeChanged = Signal()
    preferencesChanged = Signal()
    batchFinished = Signal(int, int)
    eraseMaskRequested = Signal(str, str, bool)
    _probeReady = Signal(object, object)

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
        self._pending_paths: list[str] = []
        self._busy = False
        self._last_error = ""
        self._notice = ""
        self._notice_kind = "info"
        self._notice_action = ""
        self._notice_timer = QTimer(self)
        self._notice_timer.setSingleShot(True)
        self._notice_timer.timeout.connect(self.dismissNotice)
        self._destination = str(self.settings.value("destination", ""))
        self._lane_limits = _lane_limits()
        self._max_parallel = max(2, min(6, (os.cpu_count() or 4) // 2))
        self._runs: dict[str, _Run] = {}
        self._ai_process: QProcess | None = None
        self._ai_stdout = ""
        self._pause_requested = False
        self._stop_requested = False
        self._batch_job_ids: set[str] = set()
        self._schedule_pending = False
        # Jobs removed while running are dropped from the list once their process exits.
        self._discard_after_cancel: set[str] = set()
        self._preferences_path = self.store.path.parent / "preferences.json"
        self._preferences = self._load_preferences()
        self._probeReady.connect(self._on_probe_ready)

    # ----------------------------------------------------------------- state

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

    @Property(int, notify=queueStateChanged)
    def pendingCount(self) -> int:
        """Jobs that Convert would start (queued, failed or cancelled)."""
        return sum(
            job.status in {JobStatus.QUEUED, JobStatus.FAILED, JobStatus.CANCELLED}
            for job in self.model.jobs
        )

    @Property(int, notify=queueStateChanged)
    def succeededCount(self) -> int:
        return sum(job.status == JobStatus.SUCCEEDED for job in self.model.jobs)

    @Property(int, notify=queueStateChanged)
    def failedCount(self) -> int:
        return sum(job.status == JobStatus.FAILED for job in self.model.jobs)

    @Property(float, notify=queueStateChanged)
    def overallProgress(self) -> float:
        jobs = [job for job in self.model.jobs if job.id in self._batch_job_ids]
        if not jobs:
            return 0.0
        done = sum(
            1.0 if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
            else job.progress if job.status == JobStatus.RUNNING
            else 0.0
            for job in jobs
        )
        return done / len(jobs)

    @Property(str, notify=queueStateChanged)
    def progressText(self) -> str:
        if not self._busy:
            return ""
        jobs = [job for job in self.model.jobs if job.id in self._batch_job_ids]
        finished = sum(
            job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
            for job in jobs
        )
        return progress_summary(finished, len(jobs), self.model.language)

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

    @Property(bool, notify=destinationChanged)
    def hasCustomDestination(self) -> bool:
        return bool(self._destination)

    @Property(str, notify=errorChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property(str, notify=noticeChanged)
    def notice(self) -> str:
        return self._notice

    @Property(str, notify=noticeChanged)
    def noticeKind(self) -> str:
        return self._notice_kind

    @Property(str, notify=noticeChanged)
    def noticeAction(self) -> str:
        return self._notice_action

    @Property(bool, notify=preferencesChanged)
    def autoStart(self) -> bool:
        return bool(self._preferences.get("auto_start", False))

    @autoStart.setter
    def autoStart(self, value: bool) -> None:
        if bool(value) == self.autoStart:
            return
        self._preferences["auto_start"] = bool(value)
        self._save_preferences()
        self.preferencesChanged.emit()

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

    @Property(int, notify=imageSettingsChanged)
    def imageTargetSizeKb(self) -> int:
        values = {job.image_options.target_size_kb for job in self._image_jobs()}
        if len(values) != 1:
            return -1
        return next(iter(values)) or 0

    # ------------------------------------------------------------- lifecycle

    def restore(self) -> None:
        self.model.replace(self.store.load())
        if self.model.jobs and not any(job.selected for job in self.model.jobs):
            self.model.jobs[0].selected = True
            self.model.refresh()
        self._structure_changed()

    def shutdown(self) -> None:
        for run in list(self._runs.values()):
            if run.process and run.process.state() != QProcess.NotRunning:
                run.process.kill()
                run.process.waitForFinished(1000)
            remove_partial_output(run.plan)
            run.job.status = JobStatus.QUEUED
            run.job.progress = 0.0
        self._runs.clear()
        if self._ai_process and self._ai_process.state() != QProcess.NotRunning:
            self._ai_process.kill()
            self._ai_process.waitForFinished(1000)
        self._set_badge(0)
        self.store.save(self.model.jobs)
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ---------------------------------------------------------------- intake

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
        if not paths:
            return
        if self._probing:
            # Files dropped while an earlier drop is still being read join the
            # next pass instead of being lost.
            self._pending_paths.extend(paths)
            return
        self._probing = True
        self.probingChanged.emit()
        existing = {job.source.path for job in self.model.jobs}

        def work() -> dict[str, object]:
            descriptors: list[FileDescriptor] = []
            unsupported: list[str] = []
            unreadable: list[str] = []
            duplicates = 0
            seen: set[str] = set()
            for path in expand_paths(paths):
                key = str(path)
                if key in existing or key in seen:
                    duplicates += 1
                    continue
                seen.add(key)
                if media_kind_for(path) not in {
                    MediaKind.IMAGE,
                    MediaKind.AUDIO,
                    MediaKind.VIDEO,
                }:
                    unsupported.append(path.name)
                    continue
                try:
                    descriptors.append(probe_file(path))
                except Exception:  # Defensive isolation: one bad file must not block the batch.
                    unreadable.append(path.name)
            return {
                "descriptors": descriptors,
                "unsupported": unsupported,
                "unreadable": unreadable,
                "duplicates": duplicates,
            }

        future = self._executor.submit(work)

        def completed(result: concurrent.futures.Future[dict[str, object]]) -> None:
            try:
                payload = result.result()
            except Exception as exc:  # pragma: no cover - executor-level failure
                payload = {"descriptors": [], "unreadable": [str(exc)]}
            self._probeReady.emit(payload, None)

        future.add_done_callback(completed)

    @Slot(object, object)
    def _on_probe_ready(self, payload: dict[str, object], _unused: object = None) -> None:
        now = time.time()
        descriptors: list[FileDescriptor] = list(payload.get("descriptors", []))  # type: ignore[arg-type]
        unsupported: list[str] = list(payload.get("unsupported", []))  # type: ignore[arg-type]
        unreadable: list[str] = list(payload.get("unreadable", []))  # type: ignore[arg-type]
        duplicates = int(payload.get("duplicates", 0))  # type: ignore[arg-type]
        additions: list[JobRecord] = []
        for index, descriptor in enumerate(descriptors):
            target = self._preferred_target(descriptor)
            if not target:
                unsupported.append(descriptor.name)
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
        self.probingChanged.emit()
        message, kind = intake_notice(unsupported, unreadable, duplicates, self.model.language)
        if message:
            self._show_notice(message, kind)
        self._set_error("\n".join(unreadable))
        self._persist()
        self._structure_changed()
        if self._pending_paths:
            pending, self._pending_paths = self._pending_paths, []
            self.add_paths(pending)
        elif additions and self.autoStart:
            self.startAll()

    # ------------------------------------------------------- format choices

    def _preferred_target(self, descriptor: FileDescriptor) -> str | None:
        """Use the format last chosen for this kind, unless it would be a no-op."""
        remembered = self._preferences.get("formats", {}).get(descriptor.kind.value)
        if remembered and is_compatible(descriptor.kind, remembered):
            if target_definition(remembered).extension != descriptor.suffix.lower():
                return remembered
        return default_target(descriptor.kind, descriptor.suffix)

    def _remember_target(self, kind: MediaKind, choice: str) -> None:
        if choice in ACTION_BY_LABEL or not is_compatible(kind, choice):
            return
        formats = self._preferences.setdefault("formats", {})
        if formats.get(kind.value) != choice:
            formats[kind.value] = choice
            self._save_preferences()

    def _load_preferences(self) -> dict:
        try:
            value = json.loads(self._preferences_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_preferences(self) -> None:
        try:
            self._preferences_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._preferences_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self._preferences, indent=2), encoding="utf-8")
            os.replace(temporary, self._preferences_path)
        except OSError:
            pass

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
        if target == ACTIONS[OperationKind.ERASE_OBJECT].label:
            self.eraseMaskRequested.emit(
                job.id, QUrl.fromLocalFile(job.source.path).toString(), False
            )
            return
        previous = (job.operation, job.target_format, dict(job.operation_options))
        if not apply_choice(job, target):
            return
        if previous == (job.operation, job.target_format, job.operation_options):
            return
        self._reset_job(job)
        self._remember_target(job.source.kind, target)
        self.model.refresh()
        self._persist()
        self.queueStateChanged.emit()

    @Slot(str, str)
    def setGroupTargetFormat(self, kind_value: str, target: str) -> None:
        try:
            kind = MediaKind(kind_value)
        except ValueError:
            return
        if not is_choice_compatible(kind, target, self.model.enabled_ai_actions):
            return
        if target == ACTIONS[OperationKind.ERASE_OBJECT].label:
            first = next(
                (
                    job
                    for job in self.model.jobs
                    if job.source.kind == kind and job.status != JobStatus.RUNNING
                ),
                None,
            )
            if first:
                self.eraseMaskRequested.emit(
                    first.id, QUrl.fromLocalFile(first.source.path).toString(), True
                )
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
        self._remember_target(kind, target)
        if changed:
            self.model.refresh()
            self._persist()
            self.queueStateChanged.emit()

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

    @Slot(int)
    def setImageTargetSizeKb(self, value: int) -> None:
        target = max(0, min(1_000_000, value)) or None
        for job in self._image_jobs():
            if job.status == JobStatus.RUNNING:
                continue
            job.image_options.target_size_kb = target
            self._reset_job(job)
        self._finish_image_settings_change()

    @Slot(str, result=str)
    def imageResizePresetFor(self, job_id: str) -> str:
        job = self._editable_image_job(job_id)
        if not job:
            return "custom"
        return {
            (100, None): "original",
            (50, None): "half",
            (100, 2048): "edge2048",
            (100, 1080): "edge1080",
        }.get((job.image_options.scale_percent, job.image_options.max_edge), "custom")

    @Slot(str, result=str)
    def imageQualityPresetFor(self, job_id: str) -> str:
        job = self._editable_image_job(job_id)
        return (
            {72: "small", 84: "balanced", 92: "best"}.get(
                job.image_options.quality, "custom"
            )
            if job
            else "custom"
        )

    @Slot(str, result=str)
    def imageCornerPresetFor(self, job_id: str) -> str:
        job = self._editable_image_job(job_id)
        return (
            {0: "none", 24: "soft", 64: "round"}.get(
                job.image_options.corner_radius, "custom"
            )
            if job
            else "custom"
        )

    @Slot(str, result=int)
    def imageTargetSizeKbFor(self, job_id: str) -> int:
        job = self._editable_image_job(job_id)
        return (job.image_options.target_size_kb or 0) if job else 0

    @Slot(str, str)
    def setJobImageResizePreset(self, job_id: str, preset: str) -> None:
        values = {
            "original": (100, None),
            "half": (50, None),
            "edge2048": (100, 2048),
            "edge1080": (100, 1080),
        }
        job = self._editable_image_job(job_id)
        if not job or preset not in values or job.status == JobStatus.RUNNING:
            return
        job.image_options.scale_percent, job.image_options.max_edge = values[preset]
        self._reset_job(job)
        self._finish_image_settings_change()

    @Slot(str, str)
    def setJobImageQualityPreset(self, job_id: str, preset: str) -> None:
        values = {"small": 72, "balanced": 84, "best": 92}
        job = self._editable_image_job(job_id)
        if not job or preset not in values or job.status == JobStatus.RUNNING:
            return
        job.image_options.quality = values[preset]
        self._reset_job(job)
        self._finish_image_settings_change()

    @Slot(str, str)
    def setJobImageCornerPreset(self, job_id: str, preset: str) -> None:
        values = {"none": 0, "soft": 24, "round": 64}
        job = self._editable_image_job(job_id)
        if not job or preset not in values or job.status == JobStatus.RUNNING:
            return
        job.image_options.corner_radius = values[preset]
        self._reset_job(job)
        self._finish_image_settings_change()

    @Slot(str, int)
    def setJobImageTargetSizeKb(self, job_id: str, value: int) -> None:
        job = self._editable_image_job(job_id)
        if not job or job.status == JobStatus.RUNNING:
            return
        job.image_options.target_size_kb = max(0, min(1_000_000, value)) or None
        self._reset_job(job)
        self._finish_image_settings_change()

    def _image_jobs(self) -> list[JobRecord]:
        return [job for job in self.model.jobs if job.source.kind == MediaKind.IMAGE]

    def _editable_image_job(self, job_id: str) -> JobRecord | None:
        job = self.model.find(job_id)
        return job if job and job.source.kind == MediaKind.IMAGE else None

    def _finish_image_settings_change(self) -> None:
        self.model.refresh()
        self._persist()
        self.imageSettingsChanged.emit()
        self.queueStateChanged.emit()

    @Slot(str, result=str)
    def eraseMaskPath(self, job_id: str) -> str:
        job = self._editable_image_job(job_id)
        if not job:
            return ""
        masks = CACHE_ROOT / "masks"
        masks.mkdir(parents=True, exist_ok=True)
        return str(masks / f"{job.id}.png")

    @Slot(str, str, bool)
    def completeEraseMask(self, job_id: str, mask_path: str, apply_group: bool) -> None:
        source_job = self._editable_image_job(job_id)
        mask = Path(mask_path)
        if not source_job or not mask.is_file():
            self._set_error("The erase mask could not be saved. Try drawing it again.")
            return
        jobs = self._image_jobs() if apply_group else [source_job]
        changed = False
        for job in jobs:
            if job.status == JobStatus.RUNNING:
                continue
            if not apply_choice(job, ACTIONS[OperationKind.ERASE_OBJECT].label):
                continue
            job.operation_options["mask_path"] = str(mask)
            self._reset_job(job)
            changed = True
        if changed:
            self._set_error("")
            self.model.refresh()
            self._persist()


    # ------------------------------------------------------- queue editing

    @Slot(str)
    def selectJob(self, job_id: str) -> None:
        changed = []
        for job in self.model.jobs:
            selected = job.id == job_id
            if job.selected != selected:
                job.selected = selected
                changed.append(job)
        for job in changed:
            self.model.refresh_job(job)

    @Slot(int)
    def moveSelection(self, step: int) -> None:
        jobs = self._display_order()
        if not jobs:
            return
        current = next((index for index, job in enumerate(jobs) if job.selected), -1)
        target = max(0, min(len(jobs) - 1, current + step if current >= 0 else 0))
        self.selectJob(jobs[target].id)

    @Slot(str)
    def removeJob(self, job_id: str) -> None:
        run = self._runs.get(job_id)
        if run:
            run.cancel_requested = True
            self._discard_after_cancel.add(job_id)
            self._stop_run(run)
            return
        jobs = self._display_order()
        index = next((i for i, job in enumerate(jobs) if job.id == job_id), -1)
        was_selected = index >= 0 and jobs[index].selected
        remaining = [job for job in self.model.jobs if job.id != job_id]
        if was_selected:
            neighbours = [job for job in jobs if job.id != job_id]
            if neighbours:
                neighbours[min(index, len(neighbours) - 1)].selected = True
        self._batch_job_ids.discard(job_id)
        self.model.replace(remaining)
        self._persist()
        self._structure_changed()

    @Slot()
    def removeSelected(self) -> None:
        job = next((item for item in self.model.jobs if item.selected), None)
        if job:
            self.removeJob(job.id)

    @Slot()
    def clearCompleted(self) -> None:
        self.model.replace(job for job in self.model.jobs if job.status != JobStatus.SUCCEEDED)
        self._persist()
        self._structure_changed()

    @Slot()
    def clearAll(self) -> None:
        if self._runs:
            self._stop_requested = True
            for job in self.model.jobs:
                if job.status == JobStatus.QUEUED:
                    job.status = JobStatus.CANCELLED
            self._discard_after_cancel = {job.id for job in self.model.jobs}
            for run in list(self._runs.values()):
                run.cancel_requested = True
                self._stop_run(run)
        self.model.replace(job for job in self.model.jobs if job.id in self._runs)
        self.dismissNotice()
        self._persist()
        self._structure_changed()

    @Slot()
    def retryFailed(self) -> None:
        for job in self.model.jobs:
            if job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
                job.status = JobStatus.QUEUED
                job.progress = 0.0
                job.error = None
        self.model.refresh()
        self._persist()
        self.startAll()

    @Slot(str)
    def retryJob(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if not job or job.status == JobStatus.RUNNING:
            return
        self._reset_job(job)
        self.model.refresh_job(job)
        self._persist()
        if self._busy:
            self._batch_job_ids.add(job.id)
            self._request_schedule()
        else:
            self.startAll()

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

    # ------------------------------------------------------------ running

    @Slot()
    def startAll(self) -> None:
        if not self.model.jobs:
            return
        if not self.adapter.available:
            self._set_error("FFmpeg is not available. Install it or set WEMUTE_FFMPEG.")
            return
        for job in self.model.jobs:
            if job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
                job.status = JobStatus.QUEUED
                job.progress = 0.0
                job.error = None
        queued = {job.id for job in self.model.jobs if job.status == JobStatus.QUEUED}
        if not queued:
            return
        if not self._busy:
            self._batch_job_ids = set()
            self._busy = True
            self._stop_requested = False
            self.busyChanged.emit()
        self._pause_requested = False
        self._batch_job_ids |= queued
        self.dismissNotice()
        self.model.refresh()
        self._schedule()

    def _request_schedule(self) -> None:
        if not self._schedule_pending:
            self._schedule_pending = True
            QTimer.singleShot(0, self._schedule)

    def _lane_for(self, job: JobRecord) -> str:
        if job.operation != OperationKind.CONVERT:
            return "ai"
        return job.source.kind.value

    def _schedule(self) -> None:
        self._schedule_pending = False
        if not self._busy:
            return
        if not (self._pause_requested or self._stop_requested):
            for job in self._display_order():
                if len(self._runs) >= self._max_parallel:
                    break
                if job.status != JobStatus.QUEUED:
                    continue
                lane = self._lane_for(job)
                active = sum(run.lane == lane for run in self._runs.values())
                if active >= self._lane_limits.get(lane, 1):
                    continue
                self._start(job, lane)
        self.queueStateChanged.emit()
        self._set_badge(
            sum(
                job.status in {JobStatus.QUEUED, JobStatus.RUNNING}
                for job in self.model.jobs
                if job.id in self._batch_job_ids
            )
        )
        if not self._runs:
            self._finish_batch()

    def _start(self, job: JobRecord, lane: str) -> None:
        source = Path(job.source.path)
        destination = Path(self._destination) if self._destination else source.parent
        try:
            plan = self.adapter.plan(job, destination)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            self.model.refresh_job(job)
            return

        job.status = JobStatus.RUNNING
        job.progress = 0.01
        job.error = None
        run = _Run(job=job, plan=plan, lane=lane)
        self._runs[job.id] = run
        self.model.refresh_job(job)

        if plan.worker_request:
            self._start_ai_request(run)
            return

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.readyReadStandardOutput.connect(lambda run=run: self._read_run_output(run))
        process.readyReadStandardError.connect(
            lambda run=run: run.stderr.extend(bytes(run.process.readAllStandardError()))
            if run.process
            else None
        )
        process.finished.connect(
            lambda code, _status, run=run: self._process_finished(run, code)
        )
        process.errorOccurred.connect(lambda _error, run=run: self._process_error(run))
        run.process = process
        process.start(plan.command[0], plan.command[1:])

    def _start_ai_request(self, run: _Run) -> None:
        process = self._ai_process
        if process is None or process.state() == QProcess.NotRunning:
            process = QProcess(self)
            process.setProcessChannelMode(QProcess.SeparateChannels)
            process.readyReadStandardOutput.connect(self._read_ai_output)
            process.readyReadStandardError.connect(self._read_ai_stderr)
            process.finished.connect(self._ai_worker_finished)
            self._ai_process = process
            self._ai_stdout = ""
            command = run.plan.server_command
            process.start(command[0], command[1:])
            if not process.waitForStarted(3000):
                self._finish_run(run, False, process.errorString() or "AI worker did not start.")
                return
        payload = json.dumps(run.plan.worker_request, separators=(",", ":")) + "\n"
        if process.write(payload.encode("utf-8")) < 0:
            self._finish_run(run, False, process.errorString() or "AI worker request failed.")

    def _set_progress(self, run: _Run, value: float) -> None:
        value = max(run.job.progress, min(0.99, value))
        if value - run.job.progress >= 0.005 or value >= 0.99:
            run.job.progress = value
            self.model.refresh_job(run.job)
            self.queueStateChanged.emit()

    def _read_run_output(self, run: _Run) -> None:
        if not run.process:
            return
        run.stdout += bytes(run.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        lines = run.stdout.split("\n")
        run.stdout = lines.pop()
        duration = run.job.source.duration or 0
        for line in lines:
            key, _, raw = line.strip().partition("=")
            try:
                if key == "wemute_progress":
                    self._set_progress(run, float(raw))
                elif key in {"out_time_us", "out_time_ms"} and duration:
                    self._set_progress(run, int(raw) / (duration * 1_000_000))
                elif key == "progress" and raw == "end":
                    self._set_progress(run, 0.99)
            except ValueError:
                continue

    def _ai_run(self) -> _Run | None:
        return next((run for run in self._runs.values() if run.plan.worker_request), None)

    @Slot()
    def _read_ai_output(self) -> None:
        process = self._ai_process
        if not process:
            return
        self._ai_stdout += bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        lines = self._ai_stdout.split("\n")
        self._ai_stdout = lines.pop()
        for line in lines:
            key, _, raw = line.strip().partition("=")
            if key == "wemute_progress":
                run = self._ai_run()
                if run:
                    try:
                        self._set_progress(run, float(raw))
                    except ValueError:
                        pass
                continue
            if key != "wemute_event":
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            run = self._runs.get(str(event.get("job_id")))
            if not run:
                continue
            if event.get("type") == "progress":
                try:
                    self._set_progress(run, float(event.get("value", 0.0)))
                except (TypeError, ValueError):
                    continue
            elif event.get("type") == "result":
                ok = bool(event.get("ok"))
                error = str(event.get("error", ""))
                QTimer.singleShot(
                    0, lambda run=run, ok=ok, error=error: self._finish_run(run, ok, error)
                )

    @Slot()
    def _read_ai_stderr(self) -> None:
        if not self._ai_process:
            return
        data = bytes(self._ai_process.readAllStandardError())
        run = self._ai_run()
        if run:
            run.stderr.extend(data)

    @Slot(int, QProcess.ExitStatus)
    def _ai_worker_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        process = self._ai_process
        self._ai_process = None
        if process:
            process.deleteLater()
        run = self._ai_run()
        if not run:
            return
        stderr = run.stderr.decode("utf-8", errors="replace").strip()
        message = stderr.splitlines()[-1] if stderr else f"AI worker exited with code {exit_code}."
        self._finish_run(run, False, "" if run.cancel_requested else message)

    def _process_finished(self, run: _Run, exit_code: int) -> None:
        process = run.process
        run.process = None
        if process:
            process.deleteLater()
        if exit_code == 0:
            self._finish_run(run, True)
            return
        message = run.stderr.decode("utf-8", errors="replace").strip()
        self._finish_run(
            run,
            False,
            message.splitlines()[-1] if message else f"FFmpeg exited with code {exit_code}.",
        )

    def _process_error(self, run: _Run) -> None:
        process = run.process
        if not process:
            return
        run.stderr.extend(process.errorString().encode("utf-8"))
        if process.error() == QProcess.FailedToStart:
            run.process = None
            process.deleteLater()
            self._finish_run(run, False, process.errorString())

    def _finish_run(self, run: _Run, succeeded: bool, error: str = "") -> None:
        if self._runs.get(run.job.id) is not run:
            return
        del self._runs[run.job.id]
        job = run.job
        plan = run.plan
        if run.cancel_requested:
            remove_partial_output(plan)
            job.status = JobStatus.CANCELLED
            job.progress = 0.0
        elif succeeded:
            try:
                job.output_size = finalize_output(plan)
                job.output_path = str(plan.final_output)
                job.status = JobStatus.SUCCEEDED
                job.progress = 1.0
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.progress = 0.0
                remove_partial_output(plan)
        else:
            stderr = run.stderr.decode("utf-8", errors="replace").strip()
            job.status = JobStatus.FAILED
            job.error = error or (stderr.splitlines()[-1] if stderr else "Conversion failed.")
            job.progress = 0.0
            remove_partial_output(plan)

        if job.id in self._discard_after_cancel:
            self._discard_after_cancel.discard(job.id)
            self._batch_job_ids.discard(job.id)
            self.model.replace(item for item in self.model.jobs if item.id != job.id)
            self._structure_changed()
        else:
            self.model.refresh_job(job)
        self._persist()
        self._request_schedule()

    def _stop_run(self, run: _Run) -> None:
        if run.plan.worker_request:
            if self._ai_process:
                self._ai_process.kill()
            else:
                self._finish_run(run, False)
            return
        process = run.process
        if not process:
            self._finish_run(run, False)
            return
        process.terminate()
        QTimer.singleShot(
            1200,
            lambda: process.kill() if process.state() != QProcess.NotRunning else None,
        )

    def _finish_batch(self) -> None:
        if not self._busy:
            return
        jobs = [job for job in self.model.jobs if job.id in self._batch_job_ids]
        stopped = self._stop_requested
        self._busy = False
        self._pause_requested = False
        self._stop_requested = False
        self._set_badge(0)
        self.busyChanged.emit()
        self.queueStateChanged.emit()
        self._persist()
        succeeded = [job for job in jobs if job.status == JobStatus.SUCCEEDED]
        failed = [job for job in jobs if job.status == JobStatus.FAILED]
        if stopped or not (succeeded or failed):
            return
        message, kind = batch_notice(
            len(succeeded),
            len(failed),
            sum(job.source.size for job in succeeded),
            sum(job.output_size or 0 for job in succeeded),
            self.model.language,
        )
        self._show_notice(
            message,
            kind,
            action="retry" if failed else "reveal",
            sticky=True,
        )
        self.batchFinished.emit(len(succeeded), len(failed))

    @Slot(str)
    def cancelJob(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if not job:
            return
        run = self._runs.get(job_id)
        if run:
            run.cancel_requested = True
            self._stop_run(run)
        elif job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
            self.model.refresh_job(job)
            self._persist()
            self._request_schedule()

    @Slot()
    def cancelCurrent(self) -> None:
        for run in list(self._runs.values()):
            self.cancelJob(run.job.id)

    @Slot()
    def cancelAll(self) -> None:
        self._stop_requested = True
        for job in self.model.jobs:
            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                self.model.refresh_job(job)
        for run in list(self._runs.values()):
            run.cancel_requested = True
            self._stop_run(run)
        self._persist()
        if not self._runs:
            self._request_schedule()

    @Slot()
    def pauseAfterCurrent(self) -> None:
        if self._busy:
            self._pause_requested = True

    # --------------------------------------------------------- finder & os

    def _output_or_source(self, job: JobRecord) -> Path:
        if job.output_path and Path(job.output_path).exists():
            return Path(job.output_path)
        return Path(job.source.path)

    @staticmethod
    def _reveal_paths(paths: list[Path]) -> None:
        existing = [str(path) for path in paths if path.exists()]
        if not existing:
            return
        if sys.platform == "darwin":
            # `open -R` selects the files in Finder instead of only opening the folder.
            QProcess.startDetached("/usr/bin/open", ["-R", *existing[:200]])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(existing[0]).parent)))

    @Slot(str)
    def revealJob(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if job:
            self._reveal_paths([self._output_or_source(job)])

    @Slot(str)
    def revealSource(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if job:
            self._reveal_paths([Path(job.source.path)])

    @Slot()
    def revealOutputs(self) -> None:
        candidates = [
            job for job in self.model.jobs if job.id in self._batch_job_ids
        ] or self.model.jobs
        outputs = [
            Path(job.output_path)
            for job in candidates
            if job.status == JobStatus.SUCCEEDED and job.output_path
        ]
        self._reveal_paths(outputs)

    @Slot(str)
    def openOutput(self, job_id: str) -> None:
        job = self.model.find(job_id)
        if job:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_or_source(job))))

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
        path = self._output_or_source(job)
        if os.name == "posix" and Path("/usr/bin/qlmanage").exists():
            QProcess.startDetached("/usr/bin/qlmanage", ["-p", str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # -------------------------------------------------------------- notices

    def _show_notice(
        self, message: str, kind: str = "info", action: str = "", sticky: bool = False
    ) -> None:
        self._notice = message
        self._notice_kind = kind
        self._notice_action = action
        self._notice_timer.stop()
        if not sticky:
            self._notice_timer.start(7000)
        self.noticeChanged.emit()

    @Slot()
    def dismissNotice(self) -> None:
        if not self._notice:
            return
        self._notice = ""
        self._notice_action = ""
        self._notice_timer.stop()
        self.noticeChanged.emit()

    @Slot()
    def runNoticeAction(self) -> None:
        action = self._notice_action
        if action == "reveal":
            self.revealOutputs()
        elif action == "retry":
            self.retryFailed()
            return
        self.dismissNotice()

    @staticmethod
    def _set_badge(count: int) -> None:
        app = QGuiApplication.instance()
        setter = getattr(app, "setBadgeNumber", None)
        if setter:
            try:
                setter(count)
            except Exception:  # pragma: no cover - platform specific
                pass

    # -------------------------------------------------------------- helpers

    def _display_order(self) -> list[JobRecord]:
        from wemute.presentation import GROUP_ORDER

        return sorted(self.model.jobs, key=lambda job: GROUP_ORDER[job.source.kind])

    def _structure_changed(self) -> None:
        self.fileCountChanged.emit()
        self.imageSettingsChanged.emit()
        self.queueStateChanged.emit()

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
        self._structure_changed()

    def _persist(self) -> None:
        self.store.save(self.model.jobs)

    def _set_error(self, message: str) -> None:
        self._last_error = message
        self.errorChanged.emit()
