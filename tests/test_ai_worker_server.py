from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from wemute.ai_worker import InferenceSessionCache, serve, upscale_image


def test_inference_session_cache_loads_each_model_once(tmp_path: Path) -> None:
    model = tmp_path / "model.onnx"
    sentinel = object()
    cache = InferenceSessionCache()

    with (
        patch("wemute.ai_worker._providers", return_value=["CPUExecutionProvider"]),
        patch("wemute.ai_worker.ort.InferenceSession", return_value=sentinel) as create,
    ):
        first = cache.session(model, "onnxruntime-u2net")
        second = cache.session(model, "onnxruntime-u2net")

    assert first is sentinel
    assert second is sentinel
    create.assert_called_once()


def test_worker_server_reuses_cache_across_requests() -> None:
    requests = "".join(
        json.dumps(
            {
                "job_id": f"job-{index}",
                "operation": "remove-background",
                "source": "/tmp/source.png",
                "destination": f"/tmp/output-{index}.png",
                "model": "/tmp/model.onnx",
                "backend": "onnxruntime-u2net",
                "options": {},
            }
        )
        + "\n"
        for index in range(2)
    )
    output = io.StringIO()
    caches: list[InferenceSessionCache] = []

    def fake_run(*args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        caches.append(args[6])
        args[7](1.0)

    with patch("wemute.ai_worker.run", side_effect=fake_run):
        assert serve(io.StringIO(requests), output) == 0

    assert len(caches) == 2
    assert caches[0] is caches[1]
    events = [json.loads(line.partition("=")[2]) for line in output.getvalue().splitlines()]
    assert [event["type"] for event in events] == ["progress", "result", "progress", "result"]
    assert all(event.get("ok", True) for event in events)


def test_upscale_worker_selects_scale_and_illustration_model(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    executable = runtime / "realesrgan-ncnn-vulkan"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"helper")
    (runtime / "models").mkdir()
    source = tmp_path / "source.tiff"
    source.write_bytes(b"source")
    destination = tmp_path / "output.png"
    commands: list[list[str]] = []

    def fake_convert(_source: Path, output: Path, _target: str) -> None:
        output.write_bytes(b"normalized")

    def fake_run(command: list[str], **_kwargs):  # noqa: ANN202, ANN003
        commands.append(command)
        Path(command[command.index("-o") + 1]).write_bytes(b"upscaled")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with (
        patch("wemute.image_worker.convert_image", side_effect=fake_convert),
        patch("wemute.ai_worker.subprocess.run", side_effect=fake_run),
    ):
        upscale_image(
            source,
            destination,
            runtime,
            {"scale": 4, "style": "illustration"},
        )

    assert destination.read_bytes() == b"upscaled"
    assert commands[0][commands[0].index("-s") + 1] == "4"
    assert commands[0][commands[0].index("-n") + 1] == "realesrgan-x4plus-anime"
