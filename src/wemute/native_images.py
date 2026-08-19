from __future__ import annotations

import platform
import subprocess
from pathlib import Path


HEIC_SUFFIXES = {".heic", ".heif"}
SIPS = Path("/usr/bin/sips")


class NativeImageCodecError(RuntimeError):
    pass


def _require_sips() -> None:
    if platform.system() != "Darwin" or not SIPS.is_file():
        raise NativeImageCodecError(
            "HEIC conversion requires the native macOS image codec in this build."
        )


def _run_sips(arguments: list[str]) -> None:
    _require_sips()
    try:
        subprocess.run(
            [str(SIPS), *arguments],
            capture_output=True,
            check=True,
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise NativeImageCodecError("The macOS HEIC codec could not process this image.") from exc


def decode_heic(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_sips(["-s", "format", "png", str(source), "--out", str(output)])


def encode_heic(source: Path, output: Path, quality: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_sips(
        [
            "-s",
            "format",
            "heic",
            "-s",
            "formatOptions",
            str(max(1, min(100, quality))),
            str(source),
            "--out",
            str(output),
        ]
    )


def heic_dimensions(source: Path) -> tuple[int, int] | None:
    _require_sips()
    try:
        result = subprocess.run(
            [str(SIPS), "-g", "pixelWidth", "-g", "pixelHeight", str(source)],
            capture_output=True,
            check=True,
            timeout=20,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    properties: dict[str, int] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key in {"pixelWidth", "pixelHeight"}:
            try:
                properties[key] = int(value.strip())
            except ValueError:
                return None
    if properties.get("pixelWidth") and properties.get("pixelHeight"):
        return properties["pixelWidth"], properties["pixelHeight"]
    return None
