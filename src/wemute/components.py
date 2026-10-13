"""On-demand conversion components (LibreOffice, Calibre, Pandoc).

Downloads reuse the verified, resumable model downloader; the verified
archive is then unpacked into a versioned runtime folder and deleted. DMGs
are mounted read-only and the app bundle is copied out with ``ditto``.
"""

from __future__ import annotations

import json
import os
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from wemute.model_packages import ModelManifest, ModelPackageError, ModelPackageManager
from wemute.paths import ASSET_ROOT, DATA_ROOT

COMPONENT_ROOT = DATA_ROOT / "components"
MARKER = ".wemute-component.json"

# (stage, completed, total); stage is "download" or "install".
ComponentProgress = Callable[[str, int, int], None]


class ComponentError(ModelPackageError):
    pass


@dataclass(frozen=True, slots=True)
class ComponentManifest:
    id: str
    name: str
    version: str
    filename: str
    download_url: str
    sha256: str
    size_bytes: int
    license: str
    license_url: str
    archive_format: str
    members: tuple[str, ...]
    executable: str
    platforms: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    # Run once after unpacking: macOS checks a freshly copied app on its first
    # launch, which can make that first real conversion fail.
    warmup: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict) -> "ComponentManifest":
        manifest = cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            version=str(payload["version"]),
            filename=str(payload["filename"]),
            download_url=str(payload["download_url"]),
            sha256=str(payload["sha256"]).lower(),
            size_bytes=int(payload["size_bytes"]),
            license=str(payload["license"]),
            license_url=str(payload["license_url"]),
            archive_format=str(payload["archive_format"]),
            members=tuple(str(item) for item in payload["members"]),
            executable=str(payload["executable"]),
            platforms=tuple(str(item) for item in payload.get("platforms", [])),
            kinds=tuple(str(item) for item in payload.get("kinds", [])),
            warmup=tuple(str(item) for item in payload.get("warmup", [])),
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if self.archive_format not in {"dmg", "zip"}:
            raise ValueError(f"Unsupported component archive: {self.archive_format}")
        for member in (*self.members, self.executable):
            path = Path(member)
            if path.is_absolute() or ".." in path.parts or not member:
                raise ValueError(f"Unsafe component member for {self.id}: {member}")
        if not any(self.executable == m or self.executable.startswith(m + "/") for m in self.members):
            raise ValueError(f"Executable of {self.id} is not inside its members")
        self.download_manifest().validate()

    def download_manifest(self) -> ModelManifest:
        return ModelManifest(
            id=self.id,
            name=self.name,
            version=self.version,
            capability="component",
            filename=self.filename,
            download_url=self.download_url,
            sha256=self.sha256,
            size_bytes=self.size_bytes,
            license=self.license,
            license_url=self.license_url,
            backend="component",
        )


def platform_tag() -> str:
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    return f"macos-{arch}" if sys.platform == "darwin" else f"{sys.platform}-{arch}"


def load_component_manifests(path: Path | None = None) -> list[ComponentManifest]:
    """Components published for this machine."""
    source = path or (ASSET_ROOT / "component-manifests.json")
    if not source.exists():
        return []
    payload = json.loads(source.read_text(encoding="utf-8"))
    manifests = [ComponentManifest.from_dict(item) for item in payload.get("components", [])]
    tag = platform_tag()
    return [item for item in manifests if not item.platforms or tag in item.platforms]


class ComponentManager:
    def __init__(
        self,
        root: Path | None = None,
        manifests: Iterable[ComponentManifest] | None = None,
    ) -> None:
        self.root = root or COMPONENT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifests = list(manifests) if manifests is not None else load_component_manifests()
        self._downloads = ModelPackageManager(
            root=self.root / "downloads",
            manifests=[item.download_manifest() for item in self._manifests],
        )
        self._installed_cache: dict[str, bool] = {}

    @property
    def manifests(self) -> tuple[ComponentManifest, ...]:
        return tuple(self._manifests)

    def manifest(self, component_id: str) -> ComponentManifest:
        for item in self._manifests:
            if item.id == component_id:
                return item
        raise KeyError(f"Unknown component: {component_id}")

    def runtime_dir(self, manifest: ComponentManifest) -> Path:
        return self.root / manifest.id / manifest.version / "runtime"

    def _marker(self, manifest: ComponentManifest) -> dict:
        try:
            return json.loads((self.runtime_dir(manifest) / MARKER).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def installed(self, manifest: ComponentManifest) -> bool:
        marker = self._marker(manifest)
        executable = self.runtime_dir(manifest) / manifest.executable
        return marker.get("sha256") == manifest.sha256 and executable.is_file()

    def executable(self, manifest: ComponentManifest) -> Path | None:
        path = self.runtime_dir(manifest) / manifest.executable
        return path if self.installed(manifest) else None

    def tools(self) -> dict[str, str]:
        return {
            item.id: str(self.runtime_dir(item) / item.executable)
            for item in self._manifests
            if self.installed(item)
        }

    def disk_usage(self, manifest: ComponentManifest) -> int:
        return int(self._marker(manifest).get("disk_bytes", 0))

    def partial_size(self, manifest: ComponentManifest) -> int:
        return self._downloads.partial_size(manifest.download_manifest())

    def install(
        self,
        manifest: ComponentManifest,
        progress: ComponentProgress | None = None,
        cancel: threading.Event | None = None,
        opener: Callable[[str], BinaryIO] | None = None,
    ) -> Path:
        if self.installed(manifest):
            return self.runtime_dir(manifest) / manifest.executable
        download = manifest.download_manifest()
        archive = self._downloads.install(
            download,
            progress=(lambda done, total: progress("download", done, total)) if progress else None,
            cancel=cancel,
            opener=opener,
        )
        if progress:
            progress("install", 0, 0)
        runtime = self.runtime_dir(manifest)
        runtime.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".install-", dir=str(runtime.parent)))
        try:
            if manifest.archive_format == "dmg":
                self._copy_from_dmg(archive, manifest, staging)
            else:
                self._extract_zip(archive, manifest, staging)
            executable = staging / manifest.executable
            if not executable.is_file():
                raise ComponentError(f"{manifest.name} is missing {manifest.executable}")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if manifest.warmup:
                try:
                    subprocess.run(
                        [str(executable), *manifest.warmup],
                        capture_output=True,
                        stdin=subprocess.DEVNULL,
                        timeout=180,
                        check=False,
                    )
                except (OSError, subprocess.SubprocessError):
                    pass
            disk = sum(item.lstat().st_size for item in staging.rglob("*") if item.is_file())
            (staging / MARKER).write_text(
                json.dumps({"sha256": manifest.sha256, "version": manifest.version, "disk_bytes": disk}),
                encoding="utf-8",
            )
            if runtime.exists():
                shutil.rmtree(runtime)
            os.rename(staging, runtime)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        # The verified archive is no longer needed once unpacked.
        self._discard_download(manifest)
        self._remove_other_versions(manifest)
        return runtime / manifest.executable

    def remove(self, manifest: ComponentManifest) -> None:
        self._discard_download(manifest)
        shutil.rmtree(self.root / manifest.id, ignore_errors=True)

    def _discard_download(self, manifest: ComponentManifest) -> None:
        self._downloads.remove(manifest.download_manifest())
        shutil.rmtree(self._downloads.root / manifest.id, ignore_errors=True)

    def _remove_other_versions(self, manifest: ComponentManifest) -> None:
        folder = self.root / manifest.id
        for child in folder.iterdir():
            if child.is_dir() and child.name != manifest.version:
                shutil.rmtree(child, ignore_errors=True)

    @staticmethod
    def _extract_zip(archive: Path, manifest: ComponentManifest, staging: Path) -> None:
        with zipfile.ZipFile(archive) as bundle:
            for member in manifest.members:
                try:
                    info = bundle.getinfo(member)
                except KeyError as exc:
                    raise ComponentError(f"{manifest.name} archive lacks {member}") from exc
                if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                    raise ComponentError(f"Unsafe member in {manifest.name}: {member}")
                destination = staging / member
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)

    @staticmethod
    def _copy_from_dmg(archive: Path, manifest: ComponentManifest, staging: Path) -> None:
        mount_root = Path(tempfile.mkdtemp(prefix="wemute-dmg-"))
        try:
            result = subprocess.run(
                [
                    "/usr/bin/hdiutil",
                    "attach",
                    "-nobrowse",
                    "-readonly",
                    "-noautoopen",
                    "-noverify",
                    "-mountrandom",
                    str(mount_root),
                    "-plist",
                    str(archive),
                ],
                input=b"Y\n",  # accept a licence prompt, if the image shows one
                capture_output=True,
                timeout=300,
                check=False,
            )
            if result.returncode != 0:
                raise ComponentError(
                    f"Could not open {manifest.name}: {result.stderr.decode(errors='replace').strip()}"
                )
            # The plist follows any licence text hdiutil may have printed.
            raw = result.stdout[result.stdout.find(b"<?xml"):]
            entities = plistlib.loads(raw).get("system-entities", [])
            mounts = [Path(item["mount-point"]) for item in entities if item.get("mount-point")]
            if not mounts:
                raise ComponentError(f"Could not mount {manifest.name}")
            mount = mounts[0]
            try:
                for member in manifest.members:
                    source = mount / member
                    if not source.exists():
                        raise ComponentError(f"{manifest.name} image lacks {member}")
                    destination = staging / member
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    copied = subprocess.run(
                        ["/usr/bin/ditto", str(source), str(destination)],
                        capture_output=True,
                        timeout=900,
                        check=False,
                    )
                    if copied.returncode != 0:
                        raise ComponentError(
                            f"Could not copy {manifest.name}: {copied.stderr.decode(errors='replace').strip()}"
                        )
            finally:
                subprocess.run(
                    ["/usr/bin/hdiutil", "detach", str(mount), "-force"],
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
        finally:
            shutil.rmtree(mount_root, ignore_errors=True)
