"""Alpha-matte helpers shared by background removal and ID photos (numpy only)."""

from __future__ import annotations

import numpy as np
from PIL import Image


def _box_sum(mask: np.ndarray, radius: int) -> np.ndarray:
    """Number of set pixels in the (2r+1)² square around every pixel."""
    padded = np.pad(mask.astype(np.int32), radius + 1)[:-1, :-1]
    integral = padded.cumsum(0).cumsum(1)
    size = 2 * radius + 1
    return (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    return _box_sum(mask, radius) > 0


def _box_mean(values: np.ndarray, radius: int) -> np.ndarray:
    padded = np.pad(values, radius + 1, mode="edge")[:-1, :-1]
    integral = padded.cumsum(0).cumsum(1)
    size = 2 * radius + 1
    total = (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )
    return total / float(size * size)


def _resize_float(values: np.ndarray, size: tuple[int, int], method: Image.Resampling) -> np.ndarray:
    return np.asarray(Image.fromarray(values.astype(np.float32), mode="F").resize(size, method))


def guided_refine(rgb: np.ndarray, alpha: np.ndarray, radius: int, eps: float = 2e-4) -> np.ndarray:
    """Snap a coarse alpha to the photo's real edges (fast colour guided filter).

    Vision's mask is computed at 512 px and upscaled, which leaves soft or
    stair-stepped borders on large photos. Only the uncertain band around the
    border is replaced; solid interior and background stay as they were.
    """
    height, width = alpha.shape
    band = dilate((alpha > 0.02) & (alpha < 0.98), radius * 2)
    if not band.any():
        return alpha
    factor = max(1, min(4, radius // 2))
    low_size = (max(1, width // factor), max(1, height // factor))
    guide = rgb.astype(np.float32) / 255.0
    low_guide = np.dstack(
        [_resize_float(guide[..., c], low_size, Image.Resampling.BOX) for c in range(3)]
    ).astype(np.float64)
    low_alpha = _resize_float(alpha, low_size, Image.Resampling.BOX).astype(np.float64)
    r = max(1, radius // factor)
    mean_i = [_box_mean(low_guide[..., c], r) for c in range(3)]
    mean_p = _box_mean(low_alpha, r)
    cov_ip = [_box_mean(low_guide[..., c] * low_alpha, r) - mean_i[c] * mean_p for c in range(3)]
    var = [[_box_mean(low_guide[..., i] * low_guide[..., j], r) - mean_i[i] * mean_i[j] for j in range(3)] for i in range(3)]
    for c in range(3):
        var[c][c] = var[c][c] + eps
    sigma = np.stack([np.stack(row, axis=-1) for row in var], axis=-2)
    coefficients = np.linalg.solve(sigma, np.stack(cov_ip, axis=-1)[..., None])[..., 0]
    offset = mean_p - np.einsum("...c,...c->...", coefficients, np.stack(mean_i, axis=-1))
    coefficients = np.dstack([_box_mean(coefficients[..., c], r) for c in range(3)])
    offset = _box_mean(offset, r)
    full_size = (width, height)
    refined = sum(
        _resize_float(coefficients[..., c], full_size, Image.Resampling.BILINEAR) * guide[..., c]
        for c in range(3)
    ) + _resize_float(offset, full_size, Image.Resampling.BILINEAR)
    refined = np.clip(refined, 0.0, 1.0)
    return np.where(band, refined, alpha).astype(np.float32)


def finish_alpha(alpha: np.ndarray) -> np.ndarray:
    """Narrow soft transitions so edges read crisp while hair strands survive,
    and snap near-solid values so the interior has no faint holes."""
    alpha = np.clip((alpha - 0.5) * 1.5 + 0.5, 0.0, 1.0)
    return np.where(alpha < 0.012, 0.0, np.where(alpha > 0.988, 1.0, alpha)).astype(np.float32)


def decontaminate_edges(rgb: np.ndarray, alpha: np.ndarray, radius: int) -> np.ndarray:
    """Remove background colour bleeding into semi-transparent edge pixels.

    Each edge pixel is a mix ``C = αF + (1 − α)B``. ``B`` and a fallback ``F``
    come from nearby clear background and solid subject pixels; solving for
    ``F`` keeps a subject shot against a green wall free of a green fringe.
    """
    edge = (alpha > 0.004) & (alpha < 0.996)
    if not edge.any():
        return rgb
    rows, cols = np.nonzero(dilate(edge, 1))
    top, bottom = rows.min(), rows.max() + 1
    left, right = cols.min(), cols.max() + 1
    pad = radius * 3 + 1
    top, left = max(0, top - pad), max(0, left - pad)
    bottom, right = min(alpha.shape[0], bottom + pad), min(alpha.shape[1], right + pad)
    a = alpha[top:bottom, left:right].astype(np.float64)
    colors = rgb[top:bottom, left:right].astype(np.float64)
    reach = radius * 3
    back_weight = (a <= 0.02).astype(np.float64)
    fore_weight = (a >= 0.98).astype(np.float64)
    back_sum = _box_mean(back_weight, reach)
    fore_sum = _box_mean(fore_weight, reach)
    solved = colors.copy()
    trust = np.clip((a - 0.15) / 0.35, 0.0, 1.0)
    for channel in range(3):
        value = colors[..., channel]
        back = _box_mean(value * back_weight, reach) / np.maximum(back_sum, 1e-6)
        fore = _box_mean(value * fore_weight, reach) / np.maximum(fore_sum, 1e-6)
        fore = np.where(fore_sum > 1e-3, fore, value)
        estimate = np.clip((value - (1.0 - a) * back) / np.maximum(a, 1e-3), 0.0, 255.0)
        estimate = trust * estimate + (1.0 - trust) * fore
        solved[..., channel] = np.where(back_sum > 1e-3, estimate, trust * value + (1.0 - trust) * fore)
    region = edge[top:bottom, left:right][..., None]
    result = rgb.copy()
    result[top:bottom, left:right] = np.where(
        region, np.clip(np.rint(solved), 0, 255).astype(np.uint8), rgb[top:bottom, left:right]
    )
    return result
