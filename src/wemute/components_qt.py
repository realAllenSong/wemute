from __future__ import annotations

import concurrent.futures
import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from wemute.components import ComponentManager
from wemute.model_packages import DownloadCancelled


def size_label(size: int) -> str:
    """Decimal units, as Finder shows them."""
    if size >= 1000**3:
        return f"{size / 1000**3:.1f} GB"
    if size >= 1000**2:
        return f"{round(size / 1000**2)} MB"
    return f"{max(1, round(size / 1000))} KB"


class ComponentController(QObject):
    """Downloads and installs conversion components one at a time."""

    catalogChanged = Signal()
    componentReady = Signal(str)
    installFailed = Signal(str, str)
    installCancelled = Signal(str)
    _progressReady = Signal(str, str, int, int)
    _installFinished = Signal(str, str)

    def __init__(self, manager: ComponentManager) -> None:
        super().__init__()
        self.manager = manager
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._cancel = threading.Event()
        self._active_id = ""
        self._queue: list[str] = []
        self._stage = ""
        self._completed = 0
        self._total = 0
        self._errors: dict[str, str] = {}
        self._installed = {item.id: manager.installed(item) for item in manager.manifests}
        self._progressReady.connect(self._on_progress)
        self._installFinished.connect(self._on_finished)

    def tools(self) -> dict[str, str]:
        return self.manager.tools()

    def known(self, component_id: str) -> bool:
        return component_id in self._installed

    def is_installed(self, component_id: str) -> bool:
        return self._installed.get(component_id, False)

    def is_pending(self, component_id: str) -> bool:
        return component_id == self._active_id or component_id in self._queue

    def status(self, component_id: str) -> dict[str, object]:
        try:
            manifest = self.manager.manifest(component_id)
        except KeyError:
            return {"id": component_id, "known": False}
        installing = component_id == self._active_id
        queued = component_id in self._queue
        progress = 0.0
        if installing and self._stage == "download" and self._total:
            progress = self._completed / self._total
        elif installing and self._stage == "install":
            progress = 1.0
        elif not self._installed[component_id]:
            progress = self.manager.partial_size(manifest) / manifest.size_bytes
        return {
            "id": component_id,
            "known": True,
            "name": manifest.name,
            "version": manifest.version,
            "sizeBytes": manifest.size_bytes,
            "sizeLabel": size_label(manifest.size_bytes),
            "diskLabel": size_label(self.manager.disk_usage(manifest)) if self._installed[component_id] else "",
            "license": manifest.license,
            "licenseUrl": manifest.license_url,
            "kinds": list(manifest.kinds),
            "installed": self._installed[component_id],
            "installing": installing,
            "queued": queued,
            "stage": self._stage if installing else "",
            "progress": progress,
            "resumable": not installing and not self._installed[component_id] and progress > 0,
            "error": self._errors.get(component_id, ""),
        }

    @Property("QVariantList", notify=catalogChanged)
    def catalog(self) -> list[dict[str, object]]:
        return [self.status(item.id) for item in self.manager.manifests]

    @Property(bool, notify=catalogChanged)
    def busy(self) -> bool:
        return bool(self._active_id)

    @Slot(str)
    def install(self, component_id: str) -> None:
        if not self.known(component_id) or self.is_installed(component_id) or self.is_pending(component_id):
            return
        self._errors.pop(component_id, None)
        self._queue.append(component_id)
        self._start_next()
        self.catalogChanged.emit()

    @Slot(str)
    def cancel(self, component_id: str) -> None:
        if component_id in self._queue:
            self._queue.remove(component_id)
            self.installCancelled.emit(component_id)
            self.catalogChanged.emit()
        elif component_id == self._active_id:
            self._cancel.set()

    @Slot(str)
    def remove(self, component_id: str) -> None:
        if not self.known(component_id) or self.is_pending(component_id):
            return
        self.manager.remove(self.manager.manifest(component_id))
        self._installed[component_id] = False
        self._errors.pop(component_id, None)
        self.catalogChanged.emit()

    def _start_next(self) -> None:
        if self._active_id or not self._queue:
            return
        component_id = self._queue.pop(0)
        manifest = self.manager.manifest(component_id)
        self._active_id = component_id
        self._stage = "download"
        self._completed = self.manager.partial_size(manifest)
        self._total = manifest.size_bytes
        self._cancel.clear()
        last = [-1.0]

        def report(stage: str, completed: int, total: int) -> None:
            fraction = completed / total if total else 0.0
            if stage == "download" and fraction - last[0] < 0.004 and completed < total:
                return
            last[0] = fraction
            self._progressReady.emit(component_id, stage, completed, total)

        def work() -> str:
            try:
                self.manager.install(manifest, progress=report, cancel=self._cancel)
                return ""
            except DownloadCancelled:
                return "cancelled"
            except Exception as exc:  # Install failures stay out of the UI process.
                return str(exc) or exc.__class__.__name__

        future = self._executor.submit(work)
        future.add_done_callback(lambda result: self._installFinished.emit(component_id, result.result()))

    @Slot(str, str, int, int)
    def _on_progress(self, component_id: str, stage: str, completed: int, total: int) -> None:
        if component_id != self._active_id:
            return
        self._stage = stage
        self._completed = completed
        self._total = total
        self.catalogChanged.emit()

    @Slot(str, str)
    def _on_finished(self, component_id: str, error: str) -> None:
        if component_id != self._active_id:
            return
        self._active_id = ""
        self._stage = ""
        self._completed = 0
        self._total = 0
        manifest = self.manager.manifest(component_id)
        self._installed[component_id] = self.manager.installed(manifest)
        if error == "cancelled":
            self.installCancelled.emit(component_id)
        elif error or not self._installed[component_id]:
            self._errors[component_id] = error or "Install failed"
            self.installFailed.emit(component_id, self._errors[component_id])
        else:
            self.componentReady.emit(component_id)
        self._start_next()
        self.catalogChanged.emit()

    def shutdown(self) -> None:
        self._queue.clear()
        self._cancel.set()
        self._executor.shutdown(wait=False, cancel_futures=True)
