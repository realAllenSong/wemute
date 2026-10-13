from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from wemute.ai_engine import apple_vision_available
from wemute.ai_worker import (
    Reporter,
    WorkerError,
    decontaminate_edges,
    finish_alpha,
    guided_refine,
    remove_background_vision,
)


needs_vision = pytest.mark.skipif(
    not apple_vision_available(), reason="Apple Vision foreground masks need macOS 14+"
)


def subject_photo(size: tuple[int, int] = (900, 600)) -> Image.Image:
    image = Image.new("RGB", size, (235, 238, 242))
    draw = ImageDraw.Draw(image)
    width, height = size
    draw.ellipse((width * 0.35, height * 0.25, width * 0.65, height * 0.7), fill=(200, 40, 40))
    draw.rectangle((width * 0.47, height * 0.68, width * 0.53, height * 0.92), fill=(60, 60, 60))
    return image


@needs_vision
def test_vision_cutout_is_full_resolution_with_a_transparent_background(tmp_path: Path) -> None:
    source = tmp_path / "subject.jpg"
    subject_photo().save(source, quality=95)
    destination = tmp_path / "cutout.png"
    events: list[dict[str, object]] = []

    remove_background_vision(source, destination, Reporter(events.append))

    with Image.open(destination) as result:
        assert result.mode == "RGBA"
        assert result.size == (900, 600)
        alpha = np.asarray(result.getchannel("A"))
    assert alpha[300, 450] == 255  # the red subject
    assert alpha[20, 20] == 0  # the plain background
    values = [event["value"] for event in events if event["type"] == "progress"]
    assert values == sorted(values) and values[-1] == 1.0
    assert [event["stage"] for event in events if event["type"] == "stage"] == ["process", "save"]


@needs_vision
def test_vision_honours_exif_orientation(tmp_path: Path) -> None:
    upright = subject_photo((900, 600))
    stored = upright.transpose(Image.Transpose.ROTATE_90)  # what the camera wrote
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise to display
    source = tmp_path / "rotated.jpg"
    stored.save(source, exif=exif, quality=95)
    destination = tmp_path / "cutout.png"

    remove_background_vision(source, destination, lambda _value: None)

    with Image.open(destination) as result:
        assert result.size == (900, 600)
        assert result.getchannel("A").getpixel((450, 300)) == 255


@needs_vision
def test_vision_reports_no_subject_with_a_stable_code(tmp_path: Path) -> None:
    source = tmp_path / "flat.png"
    Image.new("RGB", (640, 480), (128, 128, 128)).save(source)

    with pytest.raises(WorkerError) as error:
        remove_background_vision(source, tmp_path / "cutout.png", lambda _value: None)

    assert error.value.code == "no_subject"
    assert str(error.value) in {"No subject found", "没有找到可以抠出的主体"}
    assert not (tmp_path / "cutout.png").exists()


def test_guided_refine_sharpens_an_upscaled_mask_along_the_photo() -> None:
    shape = Image.new("L", (800, 800), 0)
    draw = ImageDraw.Draw(shape)
    draw.ellipse((160, 160, 640, 640), fill=255)
    for strand in range(8):  # thin hair-like strands
        draw.line([(400 + strand * 24, 180), (460 + strand * 28, 20)], fill=255, width=3)
    truth = np.asarray(shape, dtype=np.float32) / 255.0
    noise = np.random.default_rng(1).normal(0, 6, (800, 800, 3))
    rgb = np.clip(np.where(truth[..., None] > 0.5, 230, 40) + noise, 0, 255).astype(np.uint8)
    # Like Vision: a low-resolution mask scaled up to the photo.
    coarse = np.asarray(
        shape.resize((170, 170), Image.Resampling.BOX).resize((800, 800), Image.Resampling.BICUBIC),
        dtype=np.float32,
    ) / 255.0

    refined = finish_alpha(guided_refine(rgb, coarse, radius=3))

    error = np.abs(refined - truth).mean()
    assert error < 0.75 * np.abs(finish_alpha(coarse) - truth).mean()
    assert refined[400, 400] == 1.0 and refined[760, 40] == 0.0


def test_decontamination_removes_background_colour_from_edges() -> None:
    green = np.array([40, 180, 90], dtype=np.float64)
    white = np.array([250, 250, 250], dtype=np.float64)
    alpha = np.tile(np.clip((np.arange(120) - 50) / 20.0, 0.0, 1.0), (60, 1))
    mixed = alpha[..., None] * white + (1.0 - alpha[..., None]) * green
    rgb = np.rint(mixed).astype(np.uint8)

    cleaned = decontaminate_edges(rgb, alpha.astype(np.float32), radius=8)

    edge = (alpha > 0.3) & (alpha < 0.9)
    # Edge pixels move back toward the subject's own white.
    assert np.abs(cleaned[edge].astype(float) - white).mean() < 20
    assert np.abs(rgb[edge].astype(float) - white).mean() > 40
