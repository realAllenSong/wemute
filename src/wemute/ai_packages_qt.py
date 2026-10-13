from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from wemute.ai_engine import AIEngineAdapter
from wemute.domain import OperationKind
from wemute.model_packages import DownloadCancelled, ModelPackageManager

# The manifest is English; Chinese names and blurbs for the 组件 page.
_ZH_TEXT = {
    "birefnet": ("高质量去背景", "更大的本地模型，适合细发丝、半透明边缘和难抠的主体。不上传任何内容。"),
    "realesrgan-photo": ("图片放大", "本地 2× 和 4× 放大，针对照片和插画调校。"),
    "lama": ("擦除物体与水印", "用画笔涂掉物体或标记，本地补全背景。请只处理你有权编辑的图片。"),
    "mlx-audio-separator": ("人声与伴奏分离", "在本地把歌曲拆成人声和伴奏两条音轨。"),
}


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
        self._language = "en"

    def set_language(self, language: str) -> None:
        if language != self._language:
            self._language = language
            self.catalogChanged.emit()

    @Property("QVariantList", notify=catalogChanged)
    def catalog(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for manifest in self.packages.manifests:
            installed = self.packages.installed(manifest)
            installing = manifest.id == self._active_id
            partial_size = self.packages.partial_size(manifest)
            name, description = manifest.name, manifest.description
            if self._language == "zh" and manifest.id in _ZH_TEXT:
                name, description = _ZH_TEXT[manifest.id]
            rows.append(
                {
                    "id": manifest.id,
                    "name": name,
                    "description": description,
                    "sizeLabel": self._size_label(manifest.size_bytes),
                    "license": manifest.license,
                    "licenseUrl": manifest.license_url,
                    "installed": installed,
                    "installing": installing,
                    "resumable": not installed and partial_size > 0,
                    "progress": (
                        self._completed / self._total
                        if installing and self._total
                        else (
                            1.0
                            if installed
                            else partial_size / manifest.size_bytes
                        )
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
