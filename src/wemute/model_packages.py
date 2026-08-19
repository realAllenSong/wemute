from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import threading
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from wemute.paths import ASSET_ROOT, MODEL_ROOT


ProgressCallback = Callable[[int, int], None]


class ModelPackageError(RuntimeError):
    """Raised when an optional AI package cannot be safely installed."""


class DownloadCancelled(ModelPackageError):
    pass


class ChecksumMismatch(ModelPackageError):
    pass


@dataclass(frozen=True, slots=True)
class ModelManifest:
    id: str
    name: str
    version: str
    capability: str
    filename: str
    download_url: str
    sha256: str
    size_bytes: int
    license: str
    license_url: str
    backend: str
    platforms: tuple[str, ...] = ()
    minimum_memory_gb: int = 8
    description: str = ""
    archive_format: str = ""
    runtime_members: tuple[str, ...] = ()
    runtime_executable: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModelManifest":
        manifest = cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            version=str(payload["version"]),
            capability=str(payload["capability"]),
            filename=str(payload["filename"]),
            download_url=str(payload["download_url"]),
            sha256=str(payload["sha256"]).lower(),
            size_bytes=int(payload["size_bytes"]),
            license=str(payload["license"]),
            license_url=str(payload["license_url"]),
            backend=str(payload["backend"]),
            platforms=tuple(str(value) for value in payload.get("platforms", [])),
            minimum_memory_gb=int(payload.get("minimum_memory_gb", 8)),
            description=str(payload.get("description", "")),
            archive_format=str(payload.get("archive_format", "")),
            runtime_members=tuple(str(value) for value in payload.get("runtime_members", [])),
            runtime_executable=str(payload.get("runtime_executable", "")),
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not self.id or not self.version or not self.filename:
            raise ValueError("Model manifests require id, version, and filename.")
        if Path(self.filename).name != self.filename:
            raise ValueError("Model filenames must not contain directories.")
        if len(self.sha256) != 64 or any(character not in "0123456789abcdef" for character in self.sha256):
            raise ValueError(f"Invalid SHA-256 for {self.id}@{self.version}.")
        if self.size_bytes <= 0:
            raise ValueError("Model package size must be positive.")
        if self.archive_format not in {"", "zip"}:
            raise ValueError(f"Unsupported archive format for {self.id}: {self.archive_format}")
        for member in (*self.runtime_members, self.runtime_executable):
            if not member:
                continue
            path = Path(member)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe runtime member for {self.id}: {member}")
        if self.archive_format and not self.runtime_members:
            raise ValueError(f"Archive package {self.id} must declare runtime members.")
        if self.runtime_executable and self.runtime_executable not in self.runtime_members:
            raise ValueError(f"Runtime executable is not declared for {self.id}.")


def load_manifests(path: Path | None = None) -> list[ModelManifest]:
    source = path or (ASSET_ROOT / "model-manifests.json")
    if not source.exists():
        return []
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("models", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Model manifest catalog must contain a list.")
    return [ModelManifest.from_dict(item) for item in rows]


class ModelPackageManager:
    """Installs versioned model files atomically and verifies every byte."""

    def __init__(
        self,
        root: Path | None = None,
        manifests: Iterable[ModelManifest] | None = None,
    ) -> None:
        self.root = root or MODEL_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifests = list(manifests) if manifests is not None else load_manifests()
        self._active_path = self.root / "active.json"
        self._verified_paths: set[Path] = set()

    @property
    def manifests(self) -> tuple[ModelManifest, ...]:
        return tuple(self._manifests)

    def manifest(self, package_id: str, version: str | None = None) -> ModelManifest:
        matches = [item for item in self._manifests if item.id == package_id]
        if version is not None:
            matches = [item for item in matches if item.version == version]
        if not matches:
            suffix = f"@{version}" if version else ""
            raise KeyError(f"Unknown model package: {package_id}{suffix}")
        return matches[-1]

    def package_path(self, manifest: ModelManifest) -> Path:
        return self.root / manifest.id / manifest.version / manifest.filename

    def partial_path(self, manifest: ModelManifest) -> Path:
        destination = self.package_path(manifest)
        return destination.with_suffix(destination.suffix + ".part")

    def runtime_path(self, manifest: ModelManifest) -> Path:
        if not manifest.archive_format:
            return self.package_path(manifest)
        if not self.installed(manifest):
            raise ModelPackageError(f"Model package is not installed: {manifest.name}")
        runtime = self.package_path(manifest).parent / "runtime"
        marker = runtime / ".wemute-package-sha256"
        try:
            ready = marker.read_text(encoding="utf-8").strip() == manifest.sha256
        except OSError:
            ready = False
        if ready and all((runtime / member).is_file() for member in manifest.runtime_members):
            return runtime
        self._extract_runtime(manifest, runtime)
        return runtime

    def partial_size(self, manifest: ModelManifest) -> int:
        partial = self.partial_path(manifest)
        try:
            return min(partial.stat().st_size, manifest.size_bytes)
        except OSError:
            return 0

    def installed(self, manifest: ModelManifest, verify: bool = True) -> bool:
        path = self.package_path(manifest)
        if not path.is_file():
            return False
        if path.stat().st_size != manifest.size_bytes:
            return False
        if not verify or path in self._verified_paths:
            return True
        if self._digest(path) != manifest.sha256:
            return False
        self._verified_paths.add(path)
        return True

    def install(
        self,
        manifest: ModelManifest,
        progress: ProgressCallback | None = None,
        cancel: threading.Event | None = None,
        opener: Callable[[str], BinaryIO] | None = None,
    ) -> Path:
        if self.installed(manifest):
            self.activate(manifest)
            return self.package_path(manifest)
        if not manifest.download_url:
            raise ModelPackageError(f"No download URL is configured for {manifest.name}.")

        destination = self.package_path(manifest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = self.partial_path(manifest)
        downloaded = self.partial_size(manifest)
        if downloaded >= manifest.size_bytes:
            partial.unlink(missing_ok=True)
            downloaded = 0
        digest = hashlib.sha256()
        if downloaded:
            with partial.open("rb") as existing:
                while chunk := existing.read(1024 * 1024):
                    digest.update(chunk)

        if opener is not None:
            # Custom openers are primarily used by deterministic tests and may
            # not implement HTTP Range. Restart conservatively in that case.
            if downloaded:
                partial.unlink(missing_ok=True)
                downloaded = 0
                digest = hashlib.sha256()
            response = opener(manifest.download_url)
        else:
            request: str | urllib.request.Request = manifest.download_url
            if downloaded:
                request = urllib.request.Request(
                    manifest.download_url,
                    headers={"Range": f"bytes={downloaded}-"},
                )
            response = urllib.request.urlopen(request)
            if downloaded and getattr(response, "status", None) != 206:
                response.close()
                partial.unlink(missing_ok=True)
                downloaded = 0
                digest = hashlib.sha256()
                response = urllib.request.urlopen(manifest.download_url)

        try:
            if progress:
                progress(downloaded, manifest.size_bytes)
            with response, partial.open("ab" if downloaded else "wb") as output:
                while chunk := response.read(1024 * 1024):
                    if cancel and cancel.is_set():
                        raise DownloadCancelled(f"Download cancelled: {manifest.name}")
                    output.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if downloaded > manifest.size_bytes:
                        raise ModelPackageError(f"Downloaded file is larger than expected: {manifest.name}")
                    if progress:
                        progress(downloaded, manifest.size_bytes)
                output.flush()
                os.fsync(output.fileno())
            if downloaded != manifest.size_bytes:
                raise ModelPackageError(
                    f"Downloaded {downloaded} bytes, expected {manifest.size_bytes}: {manifest.name}"
                )
            if digest.hexdigest() != manifest.sha256:
                raise ChecksumMismatch(f"SHA-256 verification failed: {manifest.name}")
            partial.replace(destination)
            self._verified_paths.add(destination)
            if manifest.archive_format:
                self.runtime_path(manifest)
            self.activate(manifest)
            return destination
        except (ChecksumMismatch,):
            partial.unlink(missing_ok=True)
            raise
        except Exception:
            # Keep a valid prefix for pause/resume and transient network errors.
            try:
                if partial.stat().st_size > manifest.size_bytes:
                    partial.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def activate(self, manifest: ModelManifest) -> None:
        if not self.installed(manifest):
            raise ModelPackageError(f"Model package is not installed: {manifest.name}")
        active = self._read_active()
        active[manifest.id] = manifest.version
        temporary = self._active_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(active, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._active_path)

    def active_manifest(self, package_id: str) -> ModelManifest | None:
        version = self._read_active().get(package_id)
        if not version:
            return None
        try:
            manifest = self.manifest(package_id, version)
        except KeyError:
            return None
        return manifest if self.installed(manifest) else None

    def remove(self, manifest: ModelManifest) -> None:
        self.package_path(manifest).unlink(missing_ok=True)
        self.partial_path(manifest).unlink(missing_ok=True)
        runtime = self.package_path(manifest).parent / "runtime"
        if runtime.exists():
            shutil.rmtree(runtime)
        self._verified_paths.discard(self.package_path(manifest))
        active = self._read_active()
        if active.get(manifest.id) == manifest.version:
            active.pop(manifest.id, None)
            self._write_active(active)

    def installed_versions(self, package_id: str) -> list[str]:
        return [
            item.version
            for item in self._manifests
            if item.id == package_id and self.installed(item, verify=False)
        ]

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def _read_active(self) -> dict[str, str]:
        try:
            payload = json.loads(self._active_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        return {str(key): str(value) for key, value in payload.items()}

    def _write_active(self, active: dict[str, str]) -> None:
        temporary = self._active_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(active, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._active_path)

    def _extract_runtime(self, manifest: ModelManifest, runtime: Path) -> None:
        if manifest.archive_format != "zip":
            raise ModelPackageError(f"Unsupported archive format: {manifest.archive_format}")
        archive_path = self.package_path(manifest)
        temporary = Path(
            tempfile.mkdtemp(prefix=".runtime-", dir=str(archive_path.parent))
        )
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in manifest.runtime_members:
                    try:
                        info = archive.getinfo(member)
                    except KeyError as exc:
                        raise ModelPackageError(
                            f"Missing runtime member in {manifest.name}: {member}"
                        ) from exc
                    mode = info.external_attr >> 16
                    if info.is_dir() or stat.S_ISLNK(mode):
                        raise ModelPackageError(
                            f"Unsafe runtime member in {manifest.name}: {member}"
                        )
                    destination = (temporary / member).resolve()
                    try:
                        destination.relative_to(temporary.resolve())
                    except ValueError as exc:
                        raise ModelPackageError(
                            f"Unsafe runtime member in {manifest.name}: {member}"
                        ) from exc
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)
            if manifest.runtime_executable:
                executable = temporary / manifest.runtime_executable
                executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            (temporary / ".wemute-package-sha256").write_text(
                manifest.sha256 + "\n", encoding="utf-8"
            )
            if runtime.exists():
                shutil.rmtree(runtime)
            temporary.replace(runtime)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
