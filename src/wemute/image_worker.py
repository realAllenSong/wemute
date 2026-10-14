from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

from wemute.native_images import HEIC_SUFFIXES, decode_heic, encode_heic


LOSSY_TARGETS = {"JPEG", "WebP", "HEIC", "AVIF"}


def _save_encoded(
    image: Image.Image,
    output: Path,
    target: str,
    quality: int,
    icc: bytes | None,
    exif: bytes | None,
    stack: ExitStack,
) -> None:
    save_kwargs: dict[str, object] = {}
    if icc:
        save_kwargs["icc_profile"] = icc
    if exif and target in {"JPEG", "TIFF", "WebP", "HEIC", "AVIF"}:
        save_kwargs["exif"] = exif

    if target == "JPEG":
        if image.mode in {"RGBA", "LA"}:
            rgba = image.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, "white")
            flattened.paste(rgba, mask=rgba.getchannel("A"))
            image = flattened
        elif image.mode != "RGB":
            image = image.convert("RGB")
        save_kwargs.update(quality=quality, optimize=True, progressive=True, subsampling=0)
        image.save(output, format="JPEG", **save_kwargs)
    elif target == "PNG":
        save_kwargs.update(optimize=True, compress_level=7)
        image.save(output, format="PNG", **save_kwargs)
    elif target == "WebP":
        save_kwargs.update(quality=quality, method=6)
        image.save(output, format="WEBP", **save_kwargs)
    elif target == "HEIC":
        temporary_directory = Path(
            stack.enter_context(tempfile.TemporaryDirectory(prefix="wemute-heic-"))
        )
        intermediate = temporary_directory / "converted.png"
        png_kwargs: dict[str, object] = {"compress_level": 3}
        if icc:
            png_kwargs["icc_profile"] = icc
        if exif:
            png_kwargs["exif"] = exif
        image.save(intermediate, format="PNG", **png_kwargs)
        encode_heic(intermediate, output, quality)
    elif target == "AVIF":
        save_kwargs.update(quality=quality)
        image.save(output, format="AVIF", **save_kwargs)
    elif target == "TIFF":
        save_kwargs.update(compression="tiff_deflate")
        try:
            image.save(output, format="TIFF", **save_kwargs)
        except (OSError, ValueError, RuntimeError):
            # libtiff refuses some EXIF fields from HEIC/camera files ("Error
            # setting from dictionary"); keep the picture and colour profile.
            save_kwargs.pop("exif", None)
            image.save(output, format="TIFF", **save_kwargs)
    elif target == "BMP":
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        image.save(output, format="BMP")
    elif target == "GIF":
        image.convert("RGBA").save(output, format="GIF", optimize=True)
    else:
        raise ValueError(f"Unsupported image target: {target}")


def _save_to_target_size(
    image: Image.Image,
    output: Path,
    target: str,
    quality: int,
    target_bytes: int,
    icc: bytes | None,
    exif: bytes | None,
    stack: ExitStack,
) -> None:
    candidates = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="wemute-size-")))
    working = image
    smallest: Path | None = None
    smallest_size: int | None = None

    for resize_round in range(10):
        if target in LOSSY_TARGETS:
            low, high = 5, max(5, quality)
            best: Path | None = None
            while low <= high:
                candidate_quality = (low + high) // 2
                candidate = candidates / (
                    f"candidate-{resize_round}-{candidate_quality}{output.suffix}"
                )
                _save_encoded(
                    working,
                    candidate,
                    target,
                    candidate_quality,
                    icc,
                    exif,
                    stack,
                )
                size = candidate.stat().st_size
                if smallest_size is None or size < smallest_size:
                    smallest, smallest_size = candidate, size
                if size <= target_bytes:
                    best = candidate
                    low = candidate_quality + 1
                else:
                    high = candidate_quality - 1
            if best is not None:
                shutil.copyfile(best, output)
                return
        else:
            candidate = candidates / f"candidate-{resize_round}{output.suffix}"
            _save_encoded(working, candidate, target, quality, icc, exif, stack)
            size = candidate.stat().st_size
            if smallest_size is None or size < smallest_size:
                smallest, smallest_size = candidate, size
            if size <= target_bytes:
                shutil.copyfile(candidate, output)
                return

        assert smallest_size is not None
        if min(working.size) <= 16:
            break
        factor = math.sqrt(target_bytes / max(1, smallest_size)) * 0.96
        factor = max(0.25, min(0.88, factor))
        resized = (
            max(1, round(working.width * factor)),
            max(1, round(working.height * factor)),
        )
        if resized == working.size:
            break
        working = working.resize(resized, Image.Resampling.LANCZOS)

    if smallest is None:
        raise RuntimeError("Unable to create a size-targeted image.")
    shutil.copyfile(smallest, output)


def convert_image(
    source: Path,
    output: Path,
    target: str,
    options: dict[str, object] | None = None,
) -> None:
    options = options or {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        opened_path = source
        if source.suffix.lower() in HEIC_SUFFIXES:
            temporary_directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="wemute-heic-")))
            opened_path = temporary_directory / "decoded.png"
            decode_heic(source, opened_path)
        opened = stack.enter_context(Image.open(opened_path))
        opened.seek(0)
        image = ImageOps.exif_transpose(opened)
        image.load()
        scale_percent = max(1, min(100, int(options.get("scale_percent", 100))))
        max_edge_value = options.get("max_edge")
        max_edge = int(max_edge_value) if max_edge_value else None
        if max_edge and max(image.size) > max_edge:
            factor = max_edge / max(image.size)
            resized = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
            image = image.resize(resized, Image.Resampling.LANCZOS)
        elif scale_percent != 100:
            resized = (
                max(1, round(image.width * scale_percent / 100)),
                max(1, round(image.height * scale_percent / 100)),
            )
            image = image.resize(resized, Image.Resampling.LANCZOS)

        corner_radius = max(0, int(options.get("corner_radius", 0)))
        if corner_radius:
            image = image.convert("RGBA")
            mask = Image.new("L", image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, image.width - 1, image.height - 1),
                radius=min(corner_radius, image.width // 2, image.height // 2),
                fill=255,
            )
            alpha = ImageChops.multiply(image.getchannel("A"), mask)
            image.putalpha(alpha)

        exif = image.getexif()
        exif.pop(0x0112, None)  # Orientation is now physically applied.
        icc = image.info.get("icc_profile")

        quality = max(1, min(100, int(options.get("quality", 84))))
        exif_bytes = exif.tobytes() if exif else None
        target_size_value = options.get("target_size_kb")
        target_size_kb = max(0, int(target_size_value)) if target_size_value else 0
        if target_size_kb:
            _save_to_target_size(
                image,
                output,
                target,
                quality,
                target_size_kb * 1024,
                icc,
                exif_bytes,
                stack,
            )
        else:
            _save_encoded(image, output, target, quality, icc, exif_bytes, stack)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wemute-image-worker")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("target")
    parser.add_argument("options", nargs="?", default="{}")
    arguments = parser.parse_args(argv)
    try:
        print("progress=continue", flush=True)
        options = json.loads(arguments.options)
        if not isinstance(options, dict):
            raise ValueError("Image options must be a JSON object.")
        convert_image(arguments.source, arguments.output, arguments.target, options)
        print("progress=end", flush=True)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
