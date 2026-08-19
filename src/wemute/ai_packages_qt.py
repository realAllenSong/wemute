from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from wemute.ai_engine import AIEngineAdapter
from wemute.domain import OperationKind
from wemute.model_packages import DownloadCancelled, ModelPackageManager


class AIModelController(QObject):
    catalogChanged = Signal()
    busyChanged = Signal()
    errorChanged = Signal()
    _progressReady = Signal(str, int, int)
    _installFinished = Signal(str, str)

    def __init__(
        self,
        packages: ModelPackageManager,
        availability_changed: Callable[[set[OperationKind]], None],
    ) -> None:
        super().__init__()
        self.packages = packages
        self.adapter = AIEngineAdapter(packages)
        self._availability_changed = availability_changed
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._cancel = threading.Event()
        self._active_id = ""
        self._completed = 0
        self._total = 0
        self._error = ""
        self._progressReady.connect(self._on_progress)
        self._installFinished.connect(self._on_finished)

    @Property("QVariantList", notify=catalogChanged)
    def catalog(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for manifest in self.packages.manifests:
            installed = self.packages.installed(manifest)
            installing = manifest.id == self._active_id
            rows.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "description": manifest.description,
                    "sizeLabel": self._size_label(manifest.size_bytes),
                    "license": manifest.license,
                    "licenseUrl": manifest.license_url,
                    "installed": installed,
                    "installing": installing,
                    "progress": (
                        self._completed / self._total
                        if installing and self._total
                        else (1.0 if installed else 0.0)
                    ),
                }
            )
        return rows

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return bool(self._active_id)

    @Property(str, notify=errorChanged)
    def lastError(self) -> str:
        return self._error

    @Slot(str)
    def installPackage(self, package_id: str) -> None:
        if self.busy:
            return
        try:
            manifest = self.packages.manifest(package_id)
        except KeyError as exc:
            self._set_error(str(exc))
            return
        self._active_id = package_id
        self._completed = 0
        self._total = manifest.size_bytes
        self._cancel.clear()
        self._set_error("")
        self.busyChanged.emit()
        self.catalogChanged.emit()

        def work() -> str:
            try:
                self.packages.install(
                    manifest,
                    progress=lambda completed, total: self._progressReady.emit(
                        package_id, completed, total
                    ),
                    cancel=self._cancel,
                )
                return ""
            except DownloadCancelled:
                return "cancelled"
            except Exception as exc:  # Download failures remain isolated from the UI process.
                return str(exc)

        future = self._executor.submit(work)
        future.add_done_callback(
            lambda result: self._installFinished.emit(package_id, result.result())
        )

    @Slot(str)
    def removePackage(self, package_id: str) -> None:
        if self.busy:
            return
        try:
            manifest = self.packages.manifest(package_id)
        except KeyError as exc:
            self._set_error(str(exc))
            return
        self.packages.remove(manifest)
        self._notify_availability()
        self.catalogChanged.emit()

    @Slot()
    def cancelInstall(self) -> None:
        self._cancel.set()

    @Slot(str, int, int)
    def _on_progress(self, package_id: str, completed: int, total: int) -> None:
        if package_id != self._active_id:
            return
        self._completed = completed
        self._total = total
        self.catalogChanged.emit()

    @Slot(str, str)
    def _on_finished(self, package_id: str, error: str) -> None:
        if package_id != self._active_id:
            return
        self._active_id = ""
        self._completed = 0
        self._total = 0
        self._set_error("" if error == "cancelled" else error)
        self._notify_availability()
        self.busyChanged.emit()
        self.catalogChanged.emit()

    def shutdown(self) -> None:
        self._cancel.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _notify_availability(self) -> None:
        self._availability_changed(self.adapter.enabled_actions())

    def _set_error(self, error: str) -> None:
        self._error = error
        self.errorChanged.emit()

    @staticmethod
    def _size_label(size: int) -> str:
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / 1024:.0f} KB"
