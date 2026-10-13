from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from wemute.ai_engine import APPLE_VISION_BACKEND, AIEngineAdapter, AIEngineUnavailableError
from wemute.domain import FileDescriptor, JobRecord, MediaKind, OperationKind
from wemute.model_packages import ModelManifest, ModelPackageManager, load_manifests


@pytest.fixture
def without_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wemute.ai_engine.apple_vision_available", lambda: False)


@pytest.fixture
def with_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wemute.ai_engine.apple_vision_available", lambda: True)


def make_manifest(
    payload: bytes,
    package_id: str = "birefnet",
    backend: str = "onnxruntime-birefnet",
) -> ModelManifest:
    return ModelManifest(
        id=package_id,
        name="Background Removal · High Quality",
        version="test",
        capability="remove-background",
        filename="model.onnx",
        download_url="memory://model",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        license="MIT",
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


def install(packages: ModelPackageManager, manifest: ModelManifest, payload: bytes) -> Path:
    path = packages.package_path(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    packages.activate(manifest)
    return path


def test_background_removal_uses_apple_vision_without_any_package(
    tmp_path: Path, with_vision: None
) -> None:
    packages = ModelPackageManager(tmp_path / "models", [])
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")
    adapter = AIEngineAdapter(packages)

    plan = adapter.plan(make_job(source), tmp_path / "out")

    assert OperationKind.REMOVE_BACKGROUND in adapter.enabled_actions()
    assert plan.worker_request["backend"] == APPLE_VISION_BACKEND
    assert APPLE_VISION_BACKEND in plan.command
    assert plan.final_output.name == "portrait remove-background.png"
    assert plan.temporary_output.name.startswith(".portrait remove-background.wemute-")


def test_apple_vision_wins_over_an_installed_model(tmp_path: Path, with_vision: None) -> None:
    payload = b"quality-model"
    manifest = make_manifest(payload)
    packages = ModelPackageManager(tmp_path / "models", [manifest])
    install(packages, manifest, payload)
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")

    plan = AIEngineAdapter(packages).plan(make_job(source), tmp_path / "out")

    assert plan.worker_request["backend"] == APPLE_VISION_BACKEND


def test_other_ai_actions_still_need_their_packages(tmp_path: Path, with_vision: None) -> None:
    adapter = AIEngineAdapter(ModelPackageManager(tmp_path / "models", []))

    assert adapter.enabled_actions() == {OperationKind.REMOVE_BACKGROUND}


def test_background_removal_falls_back_to_installed_model(
    tmp_path: Path, without_vision: None
) -> None:
    payload = b"model"
    manifest = make_manifest(payload)
    packages = ModelPackageManager(tmp_path / "models", [manifest])
    model_path = install(packages, manifest, payload)
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")

    plan = AIEngineAdapter(packages).plan(make_job(source), tmp_path / "out")

    assert model_path.as_posix() in plan.command
    assert "onnxruntime-birefnet" in plan.command
    assert "remove-background" in plan.command


def test_ai_plan_refuses_uninstalled_package(tmp_path: Path, without_vision: None) -> None:
    manifest = make_manifest(b"model")
    packages = ModelPackageManager(tmp_path / "models", [manifest])
    source = tmp_path / "portrait.jpg"
    source.write_bytes(b"image")

    assert OperationKind.REMOVE_BACKGROUND not in AIEngineAdapter(packages).enabled_actions()
    with pytest.raises(AIEngineUnavailableError, match="Install"):
        AIEngineAdapter(packages).plan(make_job(source), tmp_path / "out")


def test_bundled_catalog_loads_without_the_u2net_package() -> None:
    manifests = load_manifests()

    ids = {manifest.id for manifest in manifests}
    assert "u2net" not in ids
    assert {"lama", "realesrgan-photo", "mlx-audio-separator"} <= ids


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
