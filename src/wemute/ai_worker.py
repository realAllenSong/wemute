from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from collections.abc import Callable, Hashable
from pathlib import Path
from typing import TextIO

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter, ImageOps


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
        self._resources: dict[Hashable, object] = {}

    def session(self, model: Path, backend: str) -> ort.InferenceSession:
        key = (model.resolve(), backend)
        session = self._sessions.get(key)
        if session is None:
            providers = _providers(model)
            try:
                session = ort.InferenceSession(str(model), providers=providers)
            except Exception:
                if "CPUExecutionProvider" not in ort.get_available_providers():
                    raise
                session = ort.InferenceSession(
                    str(model), providers=["CPUExecutionProvider"]
                )
            self._sessions[key] = session
        return session

    def resource(self, key: Hashable, factory: Callable[[], object]) -> object:
        resource = self._resources.get(key)
        if resource is None:
            resource = factory()
            self._resources[key] = resource
        return resource


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


def upscale_image(
    source: Path,
    destination: Path,
    runtime: Path,
    options: dict[str, object],
    progress: ProgressCallback = _progress,
) -> None:
    executable = runtime / "realesrgan-ncnn-vulkan"
    models = runtime / "models"
    if not executable.is_file() or not models.is_dir():
        raise FileNotFoundError("The Real-ESRGAN runtime is incomplete. Reinstall the AI package.")
    scale = int(options.get("scale", 2))
    if scale not in {2, 4}:
        raise ValueError("Real-ESRGAN scale must be 2 or 4.")
    style = str(options.get("style", "photo"))
    model_name = (
        "realesrgan-x4plus-anime" if style == "illustration" else "realesrgan-x4plus"
    )
    progress(0.06)
    with tempfile.TemporaryDirectory(prefix="wemute-upscale-") as temporary_directory:
        normalized = Path(temporary_directory) / "input.png"
        from wemute.image_worker import convert_image

        convert_image(source, normalized, "PNG")
        destination.parent.mkdir(parents=True, exist_ok=True)
        progress(0.12)
        result = subprocess.run(
            [
                str(executable),
                "-i",
                str(normalized),
                "-o",
                str(destination),
                "-s",
                str(scale),
                "-m",
                str(models),
                "-n",
                model_name,
                "-f",
                "png",
            ],
            cwd=runtime,
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(message.splitlines()[-1] if message else "Real-ESRGAN failed.")
    if not destination.is_file():
        raise RuntimeError("Real-ESRGAN did not produce an output image.")
    progress(1.0)


def erase_object(
    source: Path,
    destination: Path,
    model: Path,
    backend: str,
    options: dict[str, object],
    sessions: InferenceSessionCache,
    progress: ProgressCallback = _progress,
) -> None:
    mask_value = options.get("mask_path")
    if not mask_value:
        raise ValueError("Draw a mask before starting object erase.")
    mask_path = Path(str(mask_value))
    if not mask_path.is_file():
        raise FileNotFoundError("The erase mask is missing. Draw it again.")
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    with Image.open(mask_path) as opened_mask:
        mask_rgba = opened_mask.convert("RGBA")
        alpha = mask_rgba.getchannel("A")
        has_transparency = "A" in opened_mask.getbands() and alpha.getextrema() != (255, 255)
        mask = alpha if has_transparency else opened_mask.convert("L")
    progress(0.12)
    rgb = image.convert("RGB")
    resized = rgb.resize((512, 512), Image.Resampling.LANCZOS)
    image_array = np.asarray(resized, dtype=np.float32)[..., ::-1] / 255.0
    image_tensor = np.transpose(image_array, (2, 0, 1))[None, ...].copy()
    mask_resized = mask.resize((512, 512), Image.Resampling.NEAREST)
    mask_tensor = (np.asarray(mask_resized, dtype=np.float32) > 0).astype(np.float32)
    mask_tensor = mask_tensor[None, None, ...]
    session = sessions.session(model, backend)
    progress(0.3)
    output = session.run(
        None,
        {
            session.get_inputs()[0].name: image_tensor,
            session.get_inputs()[1].name: mask_tensor,
        },
    )[0]
    progress(0.84)
    result_array = np.transpose(output[0], (1, 2, 0))[..., ::-1]
    result = Image.fromarray(np.uint8(np.clip(result_array, 0, 255)), mode="RGB")
    result = result.resize(image.size, Image.Resampling.LANCZOS)
    composite_mask = mask.resize(image.size, Image.Resampling.LANCZOS).filter(
        ImageFilter.GaussianBlur(radius=1.0)
    )
    composed = Image.composite(result, rgb, composite_mask)
    if image.getchannel("A").getextrema() != (255, 255):
        composed.putalpha(image.getchannel("A"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    composed.save(destination, "PNG", optimize=True)
    progress(1.0)


def _load_mlx_separator(runtime: Path) -> object:
    from demucs_mlx.mlx_convert import load_mlx_model_from_safetensors

    return load_mlx_model_from_safetensors(
        "htdemucs",
        cache_dir=str(runtime),
        verbose=False,
    )


def _apply_mlx_separator(model: object, source: Path) -> tuple[np.ndarray, np.ndarray, int]:
    import mlx.core as mx
    import mlx_audio_io as mac
    from demucs_mlx.apply_mlx import apply_model

    sample_rate = int(getattr(model, "samplerate", 44_100))
    audio, loaded_rate = mac.load(str(source), sr=sample_rate, dtype="float32")
    sample_rate = int(loaded_rate)
    audio_array = np.asarray(audio, dtype=np.float32)
    if audio_array.ndim == 1:
        audio_array = audio_array[:, None]
    expected_channels = int(getattr(model, "audio_channels", 2))
    if audio_array.shape[1] == 1 and expected_channels == 2:
        audio_array = np.repeat(audio_array, 2, axis=1)
    elif audio_array.shape[1] != expected_channels:
        audio_array = audio_array[:, :expected_channels]
    mix = mx.array(np.ascontiguousarray(audio_array.T[None, ...]))
    estimates = apply_model(
        model,
        mix,
        shifts=0,
        split=True,
        overlap=0.25,
        progress=False,
        batch_size=1,
        seed=0,
    )
    mx.eval(estimates)
    stems = np.asarray(estimates[0], dtype=np.float32)
    sources = list(getattr(model, "sources", ("drums", "bass", "other", "vocals")))
    try:
        vocal_index = sources.index("vocals")
    except ValueError as exc:
        raise RuntimeError("The separation model does not provide a vocals stem.") from exc
    vocals = stems[vocal_index]
    instrumental = np.sum(np.delete(stems, vocal_index, axis=0), axis=0)
    return vocals, instrumental, sample_rate


def _save_audio_stem(audio: np.ndarray, destination: Path, sample_rate: int) -> None:
    from demucs_mlx.audio import save_audio

    # demucs-mlx currently maps 24/32-bit requests to float WAV.
    # PCM16 has the widest playback compatibility across Finder, browsers,
    # editors, and the bundled FFmpeg probe path.
    save_audio(audio, destination, sample_rate, clip="clamp", bits_per_sample=16)


def separate_vocals(
    source: Path,
    vocals_destination: Path,
    runtime: Path,
    options: dict[str, object],
    sessions: InferenceSessionCache,
    progress: ProgressCallback = _progress,
) -> None:
    instrumental_value = options.get("instrumental_destination")
    if not instrumental_value:
        raise ValueError("The instrumental output destination is missing.")
    instrumental_destination = Path(str(instrumental_value))
    weights = runtime / "htdemucs.safetensors"
    config = runtime / "htdemucs_config.json"
    if not weights.is_file() or not config.is_file():
        raise FileNotFoundError("The vocal separation package is incomplete. Reinstall it.")
    progress(0.05)
    model = sessions.resource(
        ("mlx-htdemucs", runtime.resolve()),
        lambda: _load_mlx_separator(runtime),
    )
    progress(0.16)
    vocals, instrumental, sample_rate = _apply_mlx_separator(model, source)
    progress(0.88)
    vocals_destination.parent.mkdir(parents=True, exist_ok=True)
    instrumental_destination.parent.mkdir(parents=True, exist_ok=True)
    _save_audio_stem(vocals, vocals_destination, sample_rate)
    progress(0.94)
    _save_audio_stem(instrumental, instrumental_destination, sample_rate)
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
    options = options or {}
    sessions = sessions or InferenceSessionCache()
    if operation == "remove-background" and backend in {
        "onnxruntime-u2net",
        "onnxruntime-birefnet",
    }:
        remove_background(source, destination, model, backend, sessions, progress)
        return
    if operation == "upscale" and backend == "realesrgan-ncnn-vulkan":
        upscale_image(source, destination, model, options, progress)
        return
    if operation == "erase-object" and backend == "onnxruntime-lama":
        erase_object(source, destination, model, backend, options, sessions, progress)
        return
    if operation == "separate-vocals" and backend == "mlx-htdemucs":
        separate_vocals(source, destination, model, options, sessions, progress)
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
