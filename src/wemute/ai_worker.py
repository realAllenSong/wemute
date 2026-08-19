from __future__ import annotations

import json
import math
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps


ProgressCallback = Callable[[float], None]


def _progress(value: float) -> None:
    print(f"wemute_progress={max(0.0, min(1.0, value)):.3f}", flush=True)


def _input_size(session: ort.InferenceSession) -> tuple[int, int]:
    shape = session.get_inputs()[0].shape
    height = int(shape[-2]) if isinstance(shape[-2], int) else 320
    width = int(shape[-1]) if isinstance(shape[-1], int) else 320
    return width, height


def _providers(model: Path) -> list[object]:
    available = ort.get_available_providers()
    providers: list[object] = []
    if "CoreMLExecutionProvider" in available:
        cache = model.parent / "coreml-cache"
        cache.mkdir(parents=True, exist_ok=True)
        providers.append(
            (
                "CoreMLExecutionProvider",
                {
                    "ModelFormat": "MLProgram",
                    "MLComputeUnits": "ALL",
                    "RequireStaticInputShapes": "1",
                    "ModelCacheDirectory": str(cache),
                },
            )
        )
    if "CPUExecutionProvider" in available:
        providers.append("CPUExecutionProvider")
    return providers or available


class InferenceSessionCache:
    def __init__(self) -> None:
        self._sessions: dict[tuple[Path, str], ort.InferenceSession] = {}

    def session(self, model: Path, backend: str) -> ort.InferenceSession:
        key = (model.resolve(), backend)
        session = self._sessions.get(key)
        if session is None:
            session = ort.InferenceSession(str(model), providers=_providers(model))
            self._sessions[key] = session
        return session


def _prepare_u2net(image: Image.Image, size: tuple[int, int]) -> np.ndarray:
    resized = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    tensor = np.asarray(resized, dtype=np.float32) / 255.0
    mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
    tensor = (tensor - mean) / std
    return np.transpose(tensor, (2, 0, 1))[None, ...]


def _normalise_mask(output: np.ndarray) -> np.ndarray:
    mask = np.squeeze(output).astype(np.float32)
    if mask.ndim == 3:
        mask = mask[0]
    if float(mask.min()) < 0.0 or float(mask.max()) > 1.0:
        mask = 1.0 / (1.0 + np.exp(-np.clip(mask, -30.0, 30.0)))
    low = float(mask.min())
    high = float(mask.max())
    if math.isclose(low, high):
        return np.zeros_like(mask)
    return (mask - low) / (high - low)


def remove_background(
    source: Path,
    destination: Path,
    model: Path,
    backend: str,
    sessions: InferenceSessionCache,
    progress: ProgressCallback = _progress,
) -> None:
    progress(0.08)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    progress(0.18)
    session = sessions.session(model, backend)
    tensor = _prepare_u2net(image, _input_size(session))
    progress(0.34)
    output = session.run(None, {session.get_inputs()[0].name: tensor})[0]
    progress(0.82)
    mask = _normalise_mask(output)
    alpha = Image.fromarray(np.uint8(np.clip(mask, 0.0, 1.0) * 255), mode="L")
    alpha = alpha.resize(image.size, Image.Resampling.LANCZOS)
    image.putalpha(alpha)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG", optimize=True)
    progress(1.0)


def run(
    operation: str,
    source: Path,
    destination: Path,
    model: Path,
    backend: str,
    options: dict[str, object] | None = None,
    sessions: InferenceSessionCache | None = None,
    progress: ProgressCallback = _progress,
) -> None:
    del options
    sessions = sessions or InferenceSessionCache()
    if operation == "remove-background" and backend in {
        "onnxruntime-u2net",
        "onnxruntime-birefnet",
    }:
        remove_background(source, destination, model, backend, sessions, progress)
        return
    raise ValueError(f"Unsupported AI worker operation/backend: {operation}/{backend}")


def _event(output: TextIO, payload: dict[str, object]) -> None:
    print(f"wemute_event={json.dumps(payload, separators=(',', ':'))}", file=output, flush=True)


def serve(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
    sessions = InferenceSessionCache()
    for raw_line in input_stream:
        if not raw_line.strip():
            continue
        job_id = ""
        try:
            request = json.loads(raw_line)
            if not isinstance(request, dict):
                raise ValueError("AI worker request must be an object.")
            job_id = str(request["job_id"])
            run(
                str(request["operation"]),
                Path(str(request["source"])),
                Path(str(request["destination"])),
                Path(str(request["model"])),
                str(request["backend"]),
                dict(request.get("options", {})),
                sessions,
                lambda value: _event(
                    output_stream,
                    {"job_id": job_id, "type": "progress", "value": value},
                ),
            )
            _event(output_stream, {"job_id": job_id, "type": "result", "ok": True})
        except Exception as exc:
            _event(
                output_stream,
                {
                    "job_id": job_id,
                    "type": "result",
                    "ok": False,
                    "error": str(exc),
                },
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if arguments == ["--serve"]:
        return serve()
    if len(arguments) != 6:
        return 2
    operation, source, destination, model, backend, raw_options = arguments
    try:
        run(
            operation,
            Path(source),
            Path(destination),
            Path(model),
            backend,
            json.loads(raw_options),
            InferenceSessionCache(),
        )
    except Exception as exc:  # Worker failures must never take down the UI process.
        print(str(exc), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
