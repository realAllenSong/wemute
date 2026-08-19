from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from wemute.ai_engine import AIEngineAdapter, AIEngineUnavailableError
from wemute.domain import FileDescriptor, JobRecord, MediaKind, OperationKind
from wemute.model_packages import ModelManifest, ModelPackageManager


def make_manifest(
    payload: bytes,
    package_id: str = "u2net",
    backend: str = "onnxruntime-u2net",
) -> ModelManifest:
    return ModelManifest(
        id=package_id,
        name="Background Removal · Fast",
        version="test",
        capability="remove-background",
        filename="u2netp.onnx",
        download_url="memory://u2netp",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        license="Apache-2.0",
        license_url="https://example.com/license",
        backend=backend,
    )


def make_job(source: Path) -> JobRecord:
    return JobRecord(
        "job-1",
        FileDescriptor(
            path=str(source),
            name=source.name,
            suffix=source.suffix,
            kind=MediaKind.IMAGE,
        ),
        "PNG",
        operation=OperationKind.REMOVE_BACKGROUND,
    )


def test_background_removal_plan_uses_verified_active_model(tmp_path: Path) -> None:
    payload = b"model"
    manifest = make_manifest(payload)
    packages = ModelPackageManager(tmp_path / "models", [manifest])
    model_path = packages.package_path(manifest)
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(payload)
    packages.activate(manifest)
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")

    plan = AIEngineAdapter(packages).plan(make_job(source), tmp_path / "out")

    assert model_path.as_posix() in plan.command
    assert "remove-background" in plan.command
    assert plan.final_output.name == "portrait remove-background.png"
    assert plan.temporary_output.name.startswith(".portrait remove-background.wemute-")


def test_ai_plan_refuses_uninstalled_package(tmp_path: Path) -> None:
    manifest = make_manifest(b"model")
    packages = ModelPackageManager(tmp_path / "models", [manifest])
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")

    with pytest.raises(AIEngineUnavailableError, match="Install"):
        AIEngineAdapter(packages).plan(make_job(source), tmp_path / "out")


def test_background_removal_prefers_installed_high_quality_model(tmp_path: Path) -> None:
    fast_payload = b"fast-model"
    quality_payload = b"quality-model"
    fast = make_manifest(fast_payload)
    quality = make_manifest(quality_payload, "birefnet", "onnxruntime-birefnet")
    packages = ModelPackageManager(tmp_path / "models", [fast, quality])
    for manifest, payload in ((fast, fast_payload), (quality, quality_payload)):
        path = packages.package_path(manifest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        packages.activate(manifest)
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")

    plan = AIEngineAdapter(packages).plan(make_job(source), tmp_path / "out")

    assert str(packages.package_path(quality)) in plan.command
    assert "onnxruntime-birefnet" in plan.command


def test_vocal_separation_plan_produces_two_unique_outputs(tmp_path: Path) -> None:
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("htdemucs.safetensors", b"weights")
        archive.writestr("htdemucs_config.json", b"{}")
        archive.writestr("demucs-license.txt", b"MIT")
        archive.writestr("NOTICE.txt", b"notice")
    payload = archive_buffer.getvalue()
    manifest = ModelManifest(
        id="mlx-audio-separator",
        name="Vocal & Instrumental Separation",
        version="test",
        capability="separate-vocals",
        filename="runtime.zip",
        download_url="memory://separator",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        license="MIT",
        license_url="https://example.com/license",
        backend="mlx-htdemucs",
        archive_format="zip",
        runtime_members=(
            "htdemucs.safetensors",
            "htdemucs_config.json",
            "demucs-license.txt",
            "NOTICE.txt",
        ),
    )
    packages = ModelPackageManager(tmp_path / "models", [manifest])
    packages.install(manifest, opener=lambda _url: io.BytesIO(payload))
    source = tmp_path / "song.mp3"
    source.write_bytes(b"audio")
    job = JobRecord(
        "job-separate",
        FileDescriptor(
            path=str(source),
            name=source.name,
            suffix=source.suffix,
            kind=MediaKind.AUDIO,
        ),
        "WAV",
        operation=OperationKind.SEPARATE_VOCALS,
    )

    plan = AIEngineAdapter(packages).plan(job, tmp_path / "out")

    assert plan.final_output.name == "song Vocals.wav"
    assert len(plan.additional_outputs) == 1
    assert plan.additional_outputs[0][1].name == "song Instrumental.wav"
    assert plan.worker_request["options"]["instrumental_destination"] == str(
        plan.additional_outputs[0][0]
    )
