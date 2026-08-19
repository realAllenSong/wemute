from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

from wemute.ai_worker import InferenceSessionCache, serve


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
