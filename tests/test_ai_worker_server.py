from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from wemute.ai_worker import (
    InferenceSessionCache,
    Reporter,
    WorkerError,
    erase_object,
    separate_vocals,
    serve,
    upscale_image,
)


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


def test_inference_cache_reuses_generic_resources() -> None:
    cache = InferenceSessionCache()
    created: list[object] = []

    def factory() -> object:
        value = object()
        created.append(value)
        return value

    assert cache.resource(("separator", "model"), factory) is cache.resource(
        ("separator", "model"), factory
    )
    assert len(created) == 1


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


class FakeHelper:
    """Stands in for realesrgan-ncnn-vulkan: writes the output, prints tile progress."""

    def __init__(self, command: list[str], stderr: bytes, returncode: int = 0) -> None:
        self.stderr = io.BufferedReader(io.BytesIO(stderr))
        self.returncode = returncode
        if returncode == 0:
            Path(command[command.index("-o") + 1]).write_bytes(b"upscaled")

    def wait(self) -> int:
        return self.returncode


def upscale_runtime(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime = tmp_path / "runtime"
    executable = runtime / "realesrgan-ncnn-vulkan"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"helper")
    (runtime / "models").mkdir()
    source = tmp_path / "source.tiff"
    source.write_bytes(b"source")
    return runtime, source, tmp_path / "output.png"


def fake_convert(_source: Path, output: Path, _target: str) -> None:
    output.write_bytes(b"normalized")


def test_upscale_worker_selects_scale_and_illustration_model(tmp_path: Path) -> None:
    runtime, source, destination = upscale_runtime(tmp_path)
    commands: list[list[str]] = []

    def fake_popen(command: list[str], **_kwargs):  # noqa: ANN202, ANN003
        commands.append(command)
        return FakeHelper(command, b"[0 Apple M3]  queueC=0[1]\n0.00%\r25.00%\r50.00%\r75.00%\n")

    with (
        patch("wemute.image_worker.convert_image", side_effect=fake_convert),
        patch("wemute.ai_worker.subprocess.Popen", side_effect=fake_popen),
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


def test_upscale_reports_each_tile_and_finishes_at_one(tmp_path: Path) -> None:
    runtime, source, destination = upscale_runtime(tmp_path)
    events: list[dict[str, object]] = []
    tiles = b"".join(f"{value:.2f}%\r".encode() for value in (0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5))

    with (
        patch("wemute.image_worker.convert_image", side_effect=fake_convert),
        patch(
            "wemute.ai_worker.subprocess.Popen",
            side_effect=lambda command, **_kwargs: FakeHelper(command, tiles),
        ),
    ):
        upscale_image(source, destination, runtime, {"scale": 2}, Reporter(events.append))

    values = [float(event["value"]) for event in events if event["type"] == "progress"]
    stages = [event["stage"] for event in events if event["type"] == "stage"]
    assert stages == ["prepare", "process"]
    assert values == sorted(values)
    assert values[-1] == 1.0
    # Eight tiles map onto distinct steps between 12 % and 97 %.
    assert len([value for value in values if 0.12 <= value < 0.97]) >= 8


def test_upscale_failure_surfaces_the_helper_message(tmp_path: Path) -> None:
    runtime, source, destination = upscale_runtime(tmp_path)

    with (
        patch("wemute.image_worker.convert_image", side_effect=fake_convert),
        patch(
            "wemute.ai_worker.subprocess.Popen",
            side_effect=lambda command, **_kwargs: FakeHelper(
                command, b"0.00%\rvkAllocateMemory failed\n", returncode=255
            ),
        ),
        pytest.raises(RuntimeError, match="vkAllocateMemory failed"),
    ):
        upscale_image(source, destination, runtime, {"scale": 2})


def test_worker_server_forwards_stage_events_and_error_codes() -> None:
    request = json.dumps(
        {
            "job_id": "job-1",
            "operation": "remove-background",
            "source": "/tmp/source.png",
            "destination": "/tmp/output.png",
            "model": "apple-vision",
            "backend": "apple-vision",
            "options": {},
        }
    )
    output = io.StringIO()

    def fake_run(*args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        reporter = args[7]
        reporter.stage("process")
        reporter.progress(0.5)
        raise WorkerError("no_subject", "No subject found", "没有找到可以抠出的主体")

    with patch("wemute.ai_worker.run", side_effect=fake_run):
        assert serve(io.StringIO(request + "\n"), output) == 0

    events = [json.loads(line.partition("=")[2]) for line in output.getvalue().splitlines()]
    assert [event["type"] for event in events] == ["stage", "progress", "result"]
    assert all(event["job_id"] == "job-1" for event in events)
    assert events[0]["stage"] == "process"
    assert events[0]["label"] in {"Processing…", "处理中…"}
    assert events[-1]["ok"] is False
    assert events[-1]["code"] == "no_subject"
    assert events[-1]["error"] in {"No subject found", "没有找到可以抠出的主体"}


def test_erase_worker_changes_only_the_masked_area(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    mask = tmp_path / "mask.png"
    output = tmp_path / "output.png"
    Image.new("RGB", (64, 48), (220, 40, 30)).save(source)
    mask_image = Image.new("L", (64, 48), 0)
    for x in range(24, 40):
        for y in range(16, 32):
            mask_image.putpixel((x, y), 255)
    mask_image.save(mask)

    class FakeInput:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeSession:
        def get_inputs(self):  # noqa: ANN201
            return [FakeInput("image"), FakeInput("mask")]

        def run(self, *_args):  # noqa: ANN002, ANN201
            return [np.zeros((1, 3, 512, 512), dtype=np.float32)]

    sessions = InferenceSessionCache()
    with patch.object(sessions, "session", return_value=FakeSession()):
        erase_object(
            source,
            output,
            tmp_path / "lama.onnx",
            "onnxruntime-lama",
            {"mask_path": str(mask)},
            sessions,
        )

    with Image.open(output) as result:
        assert result.convert("RGB").getpixel((0, 0)) == (220, 40, 30)
        assert max(result.convert("RGB").getpixel((32, 24))) < 10


def test_vocal_separation_writes_both_stems_and_reuses_model(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "htdemucs.safetensors").write_bytes(b"weights")
    (runtime / "htdemucs_config.json").write_text("{}")
    source = tmp_path / "mix.wav"
    source.write_bytes(b"audio")
    vocals = tmp_path / "Vocals.wav"
    instrumental = tmp_path / "Instrumental.wav"
    sessions = InferenceSessionCache()
    model = object()
    progress: list[float] = []

    def fake_save(audio: np.ndarray, destination: Path, sample_rate: int) -> None:
        assert audio.shape == (2, 12)
        assert sample_rate == 44_100
        destination.write_bytes(b"wave")

    with (
        patch("wemute.ai_worker._load_mlx_separator", return_value=model) as load,
        patch(
            "wemute.ai_worker._apply_mlx_separator",
            return_value=(
                np.ones((2, 12), dtype=np.float32),
                np.zeros((2, 12), dtype=np.float32),
                44_100,
            ),
        ),
        patch("wemute.ai_worker._save_audio_stem", side_effect=fake_save),
    ):
        for index in range(2):
            separate_vocals(
                source,
                vocals.with_stem(f"Vocals {index}"),
                runtime,
                {
                    "instrumental_destination": str(
                        instrumental.with_stem(f"Instrumental {index}")
                    )
                },
                sessions,
                progress.append,
            )

    load.assert_called_once_with(runtime)
    assert progress[-1] == 1.0
