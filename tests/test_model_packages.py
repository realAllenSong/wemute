from __future__ import annotations

import hashlib
import io
import threading
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from wemute.model_packages import (
    ChecksumMismatch,
    DownloadCancelled,
    ModelManifest,
    ModelPackageManager,
)


class BytesResponse(io.BytesIO):
    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *_args):  # noqa: ANN001, ANN204
        self.close()


def manifest_for(payload: bytes, version: str = "1.0") -> ModelManifest:
    return ModelManifest(
        id="test-model",
        name="Test Model",
        version=version,
        capability="remove-background",
        filename="model.onnx",
        download_url="memory://model",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        license="Apache-2.0",
        license_url="https://example.com/license",
        backend="onnxruntime",
    )


def test_install_verifies_and_activates_atomically(tmp_path: Path) -> None:
    payload = b"verified-model-weights"
    manifest = manifest_for(payload)
    progress: list[tuple[int, int]] = []
    manager = ModelPackageManager(tmp_path, [manifest])

    installed = manager.install(
        manifest,
        progress=lambda completed, total: progress.append((completed, total)),
        opener=lambda _url: BytesResponse(payload),
    )

    assert installed.read_bytes() == payload
    assert manager.installed(manifest)
    assert manager.active_manifest(manifest.id) == manifest
    assert progress[-1] == (len(payload), len(payload))
    assert not installed.with_suffix(".onnx.part").exists()


def test_bad_checksum_removes_partial_file(tmp_path: Path) -> None:
    payload = b"expected"
    manifest = manifest_for(payload)
    manager = ModelPackageManager(tmp_path, [manifest])

    with pytest.raises(ChecksumMismatch):
        manager.install(manifest, opener=lambda _url: BytesResponse(b"tampered"))

    assert not manager.package_path(manifest).exists()
    assert not manager.package_path(manifest).with_suffix(".onnx.part").exists()


def test_cancelled_download_is_recoverable(tmp_path: Path) -> None:
    payload = b"cancel-me"
    manifest = manifest_for(payload)
    manager = ModelPackageManager(tmp_path, [manifest])
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(DownloadCancelled):
        manager.install(manifest, cancel=cancel, opener=lambda _url: BytesResponse(payload))

    assert not manager.package_path(manifest).exists()
    assert manager.partial_path(manifest).exists()


def test_interrupted_download_resumes_with_http_range(tmp_path: Path) -> None:
    payload = b"verified-resumable-model"
    manifest = manifest_for(payload)
    manager = ModelPackageManager(tmp_path, [manifest])
    partial = manager.partial_path(manifest)
    partial.parent.mkdir(parents=True)
    partial.write_bytes(payload[:9])

    response = BytesResponse(payload[9:])
    response.status = 206  # type: ignore[attr-defined]

    def open_range(request: object) -> BytesResponse:
        assert isinstance(request, urllib.request.Request)
        assert request.get_header("Range") == "bytes=9-"
        return response

    with patch("wemute.model_packages.urllib.request.urlopen", side_effect=open_range):
        installed = manager.install(manifest)

    assert installed.read_bytes() == payload
    assert not partial.exists()


def test_multiple_installed_versions_support_rollback(tmp_path: Path) -> None:
    first_payload = b"version-one"
    second_payload = b"version-two"
    first = manifest_for(first_payload, "1.0")
    second = manifest_for(second_payload, "2.0")
    manager = ModelPackageManager(tmp_path, [first, second])
    manager.install(first, opener=lambda _url: BytesResponse(first_payload))
    manager.install(second, opener=lambda _url: BytesResponse(second_payload))

    assert manager.active_manifest(first.id) == second
    manager.activate(first)
    assert manager.active_manifest(first.id) == first
    assert manager.installed_versions(first.id) == ["1.0", "2.0"]
