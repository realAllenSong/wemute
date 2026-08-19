from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps
from pillow_heif import register_heif_opener


register_heif_opener()


def convert_image(
    source: Path,
    output: Path,
    target: str,
    options: dict[str, object] | None = None,
) -> None:
    options = options or {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
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

        save_kwargs: dict[str, object] = {}
        if icc:
            save_kwargs["icc_profile"] = icc
        if exif and target in {"JPEG", "TIFF", "WebP", "HEIC", "AVIF"}:
            save_kwargs["exif"] = exif.tobytes()

        quality = max(1, min(100, int(options.get("quality", 84))))
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
            save_kwargs.update(quality=quality)
            image.save(output, format="HEIF", **save_kwargs)
        elif target == "AVIF":
            save_kwargs.update(quality=quality)
            image.save(output, format="AVIF", **save_kwargs)
        elif target == "TIFF":
            save_kwargs.update(compression="tiff_deflate")
            image.save(output, format="TIFF", **save_kwargs)
        elif target == "BMP":
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            image.save(output, format="BMP")
        elif target == "GIF":
            image.convert("RGBA").save(output, format="GIF", optimize=True)
        else:
            raise ValueError(f"Unsupported image target: {target}")


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
