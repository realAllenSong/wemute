from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path

from wemute.capabilities import ACTIONS, unique_output_path
from wemute.domain import ConversionPlan, JobRecord, OperationKind
from wemute.model_packages import ModelManifest, ModelPackageManager


APPLE_VISION_BACKEND = "apple-vision"
# Built into macOS, so these actions need no download.
SYSTEM_BACKENDS: dict[OperationKind, str] = {
    OperationKind.REMOVE_BACKGROUND: APPLE_VISION_BACKEND,
}


class AIEngineUnavailableError(RuntimeError):
    pass


def apple_vision_available() -> bool:
    """Vision foreground instance masks need macOS 14 and the PyObjC binding."""
    if sys.platform != "darwin":
        return False
    try:
        major = int(platform.mac_ver()[0].split(".")[0])
    except ValueError:
        return False
    return major >= 14 and importlib.util.find_spec("Vision") is not None


class AIEngineAdapter:
    def __init__(self, packages: ModelPackageManager | None = None) -> None:
        self.packages = packages or ModelPackageManager()

    def system_backend(self, operation: OperationKind) -> str | None:
        backend = SYSTEM_BACKENDS.get(operation)
        if backend == APPLE_VISION_BACKEND and apple_vision_available():
            return backend
        return None

    def enabled_actions(self) -> set[OperationKind]:
        enabled: set[OperationKind] = set()
        for operation, definition in ACTIONS.items():
            if self.system_backend(operation) or any(
                self.packages.active_manifest(package_id) for package_id in definition.package_ids
            ):
                enabled.add(operation)
        return enabled

    def plan(self, job: JobRecord, destination: Path) -> ConversionPlan:
        if job.operation == OperationKind.CONVERT:
            raise ValueError("Conversion jobs must use the media engine.")
        definition = ACTIONS.get(job.operation)
        if not definition or definition.kind != job.source.kind:
            raise ValueError(f"Unsupported AI action: {job.operation.value}")
        backend = self.system_backend(job.operation)
        if backend:
            runtime_path = Path(backend)
        else:
            manifest = self._active_manifest(definition.package_ids, definition.label)
            backend = manifest.backend
            runtime_path = self.packages.runtime_path(manifest)
        source = Path(job.source.path)
        destination.mkdir(parents=True, exist_ok=True)
        if job.operation == OperationKind.SEPARATE_VOCALS:
            final = unique_output_path(
                source,
                destination,
                definition.output_extension,
                suffix=" Vocals",
            )
            instrumental_final = unique_output_path(
                source,
                destination,
                definition.output_extension,
                suffix=" Instrumental",
            )
        else:
            final = unique_output_path(
                source,
                destination,
                definition.output_extension,
                suffix=f" {job.operation.value}",
            )
            instrumental_final = None
        temporary = final.with_name(f".{final.stem}.wemute-{job.id[:8]}{final.suffix}")
        instrumental_temporary = None
        operation_options = dict(job.operation_options)
        if instrumental_final is not None:
            instrumental_temporary = instrumental_final.with_name(
                f".{instrumental_final.stem}.wemute-{job.id[:8]}{instrumental_final.suffix}"
            )
            operation_options["instrumental_destination"] = str(instrumental_temporary)
        worker_arguments = [
            job.operation.value,
            str(source),
            str(temporary),
            str(runtime_path),
            backend,
            json.dumps(operation_options, separators=(",", ":")),
        ]
        if getattr(sys, "frozen", False):
            command = [sys.executable, "--ai-worker", *worker_arguments]
            server_command = [sys.executable, "--ai-worker-server"]
        else:
            command = [sys.executable, "-m", "wemute.ai_worker", *worker_arguments]
            server_command = [sys.executable, "-m", "wemute.ai_worker", "--serve"]
        request = {
            "job_id": job.id,
            "operation": job.operation.value,
            "source": str(source),
            "destination": str(temporary),
            "model": str(runtime_path),
            "backend": backend,
            "options": operation_options,
        }
        return ConversionPlan(
            job.id,
            source,
            temporary,
            final,
            command,
            server_command,
            request,
            (
                [(instrumental_temporary, instrumental_final)]
                if instrumental_temporary is not None and instrumental_final is not None
                else []
            ),
        )

    def _active_manifest(self, package_ids: tuple[str, ...], label: str) -> ModelManifest:
        manifest = next(
            (
                candidate
                for package_id in package_ids
                if (candidate := self.packages.active_manifest(package_id)) is not None
            ),
            None,
        )
        if manifest is not None:
            return manifest
        names: list[str] = []
        for package_id in package_ids:
            try:
                names.append(self.packages.manifest(package_id).name)
            except KeyError:
                continue
        if not names:
            names.append(label)
        raise AIEngineUnavailableError(
            f"Install {' or '.join(names)} from AI Tools before starting this action."
        )
