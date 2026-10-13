from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

from wemute.ai_worker import (
    LAMA_SIZE,
    InferenceSessionCache,
    Reporter,
    context_crop,
    dilate,
    erase_object,
    erase_regions,
    plan_regions,
)


def noisy_photo(width: int, height: int, seed: int = 7) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (height, width, 3), dtype=np.uint8)


def grey_inpaint(calls: list[tuple[np.ndarray, np.ndarray]]):  # noqa: ANN201
    def inpaint(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        assert image.shape == (1, 3, LAMA_SIZE, LAMA_SIZE)
        assert mask.shape == (1, 1, LAMA_SIZE, LAMA_SIZE)
        calls.append((image, mask))
        return np.full((1, 3, LAMA_SIZE, LAMA_SIZE), 128.0, dtype=np.float32)

    return inpaint


def test_pixels_outside_the_painted_area_stay_identical() -> None:
    photo = noisy_photo(1600, 1100)
    mask = np.zeros((1100, 1600), dtype=bool)
    mask[200:260, 300:420] = True  # a stroke near the top left
    mask[800:1000, 1200:1260] = True  # a separate stroke far away
    calls: list[tuple[np.ndarray, np.ndarray]] = []

    result = erase_regions(photo, mask, grey_inpaint(calls))

    # The paste reaches only a few pixels past the stroke (dilation + feather).
    untouched = ~dilate(mask, 16)
    assert np.array_equal(result[untouched], photo[untouched])
    assert np.all(result[mask] == 128)
    assert len(calls) == 2


def test_each_crop_keeps_context_and_full_resolution() -> None:
    width, height = 4000, 3000
    box = (1000, 1000, 1100, 1060)

    left, top, right, bottom = context_crop(box, width, height)

    assert (right - left, bottom - top) == (LAMA_SIZE, LAMA_SIZE)
    assert left <= box[0] and top <= box[1] and right >= box[2] and bottom >= box[3]
    big = context_crop((100, 100, 900, 700), width, height)
    assert big[2] - big[0] >= 1600  # at least twice the painted box
    edge = context_crop((3950, 2950, 4000, 3000), width, height)
    assert edge[2] == width and edge[3] == height  # clamped, never padded outside


def test_small_image_crop_is_clamped_to_the_image() -> None:
    assert context_crop((10, 10, 40, 30), 300, 200) == (0, 0, 300, 200)


def test_nearby_strokes_share_one_pass_and_distant_ones_do_not() -> None:
    mask = np.zeros((3000, 4000), dtype=bool)
    mask[500:540, 500:560] = True
    mask[600:640, 620:700] = True  # close to the first: same region
    mask[2400:2440, 3300:3360] = True  # far away: its own region

    regions = plan_regions(mask)

    assert len(regions) == 2
    assert regions[0][:2] == (500, 500)
    assert regions[1][:2] == (3300, 2400)


def test_long_thin_strokes_are_inpainted_in_pieces() -> None:
    mask = np.zeros((1800, 2400), dtype=bool)
    mask[1550:1660, 1170:2360] = True  # a watermark line of text

    regions = plan_regions(mask)

    assert len(regions) >= 4
    for region in regions:
        left, top, right, bottom = context_crop(region, 2400, 1800)
        assert right - left == LAMA_SIZE  # each piece is inpainted at about 1:1
    assert min(region[0] for region in regions) == 1170
    assert max(region[2] for region in regions) == 2360


def test_neighbouring_strokes_are_holes_even_when_not_pasted() -> None:
    photo = noisy_photo(2400, 600)
    mask = np.zeros((600, 2400), dtype=bool)
    mask[280:320, 200:2200] = True
    calls: list[tuple[np.ndarray, np.ndarray]] = []

    erase_regions(photo, mask, grey_inpaint(calls))

    assert len(calls) > 2
    for _image, hole in calls[1:-1]:
        # Middle pieces see the band masked across the whole crop, not only their own part.
        assert hole[0, 0, LAMA_SIZE // 2].min() == 1.0


def test_erase_object_keeps_alpha_and_untouched_pixels(tmp_path: Path) -> None:
    rgba = np.dstack([noisy_photo(900, 700), np.full((700, 900), 200, dtype=np.uint8)])
    source = tmp_path / "source.png"
    Image.fromarray(rgba, mode="RGBA").save(source)
    mask_image = Image.new("RGBA", (900, 700), (0, 0, 0, 0))
    ImageDraw.Draw(mask_image).line([(400, 300), (520, 360)], fill=(255, 255, 255, 255), width=30)
    mask_path = tmp_path / "mask.png"
    mask_image.save(mask_path)
    output = tmp_path / "output.png"

    class FakeInput:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeSession:
        def get_inputs(self):  # noqa: ANN201
            return [FakeInput("image"), FakeInput("mask")]

        def run(self, *_args):  # noqa: ANN002, ANN201
            return [np.full((1, 3, 512, 512), 64.0, dtype=np.float32)]

    sessions = InferenceSessionCache()
    events: list[dict[str, object]] = []
    with patch.object(sessions, "session", return_value=FakeSession()):
        erase_object(
            source,
            output,
            tmp_path / "lama.onnx",
            "onnxruntime-lama",
            {"mask_path": str(mask_path)},
            sessions,
            Reporter(events.append),
        )

    result = np.asarray(Image.open(output))
    painted = np.asarray(mask_image)[..., 3] > 0
    untouched = ~dilate(painted, 16)
    assert result.shape == rgba.shape
    assert np.array_equal(result[untouched], rgba[untouched])
    assert np.all(result[..., 3] == 200)
    assert np.all(result[painted][:, :3] == 64)
    stages = [event["stage"] for event in events if event["type"] == "stage"]
    assert stages == ["prepare", "process", "save"]
    values = [event["value"] for event in events if event["type"] == "progress"]
    assert values == sorted(values) and values[-1] == 1.0


def test_on_screen_sized_masks_are_scaled_to_the_photo(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.fromarray(noisy_photo(1200, 800)).save(source)
    small_mask = Image.new("L", (300, 200), 0)
    ImageDraw.Draw(small_mask).rectangle((100, 50, 140, 90), fill=255)
    mask_path = tmp_path / "mask.png"
    small_mask.save(mask_path)

    from wemute.ai_worker import load_erase_mask

    mask = load_erase_mask(mask_path, (1200, 800))

    assert mask.shape == (800, 1200)
    assert mask[280, 480] and not mask[100, 100]
