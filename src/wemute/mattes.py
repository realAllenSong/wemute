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


def color_difference_alpha(rgb: np.ndarray, alpha: np.ndarray, radius: int) -> np.ndarray:
    """Re-derive alpha in the uncertain band from colour, like a chroma key.

    Person segmentation is soft around loose hair, so dark strands come out
    half transparent and turn the new backdrop's colour (red hair on a red
    ID photo). With ``B`` the nearby original backdrop and ``F`` the nearby
    solid subject colour, a pixel ``C`` is ``α = (C − B)·(F − B) / |F − B|²``.
    It is only trusted where subject and backdrop are clearly different.
    """
    band = dilate((alpha > 0.004) & (alpha < 0.996), radius * 2)
    if not band.any():
        return alpha
    rows, cols = np.nonzero(band)
    reach = radius * 6
    top, left = max(0, rows.min() - reach), max(0, cols.min() - reach)
    bottom = min(alpha.shape[0], rows.max() + 1 + reach)
    right = min(alpha.shape[1], cols.max() + 1 + reach)
    a = alpha[top:bottom, left:right].astype(np.float64)
    colors = rgb[top:bottom, left:right].astype(np.float64)
    back_weight = (a <= 0.02).astype(np.float64)
    fore_weight = (a >= 0.98).astype(np.float64)
    back_sum = _box_mean(back_weight, reach)
    fore_sum = _box_mean(fore_weight, reach)
    back = np.dstack([_box_mean(colors[..., c] * back_weight, reach) for c in range(3)])
    fore = np.dstack([_box_mean(colors[..., c] * fore_weight, reach) for c in range(3)])
    back /= np.maximum(back_sum, 1e-6)[..., None]
    fore /= np.maximum(fore_sum, 1e-6)[..., None]
    span = fore - back
    length2 = np.einsum("...c,...c->...", span, span)
    keyed = np.einsum("...c,...c->...", colors - back, span) / np.maximum(length2, 1e-6)
    keyed = np.clip(keyed, 0.0, 1.0)
    # Fade trust in from a colour distance of 40 to 80 (out of ~441).
    trust = np.clip((np.sqrt(length2) - 40.0) / 40.0, 0.0, 1.0)
    trust *= (back_sum > 1e-3) & (fore_sum > 1e-3)
    local_band = band[top:bottom, left:right]
    mixed = np.where(local_band, trust * keyed + (1.0 - trust) * a, a)
    result = alpha.copy()
    result[top:bottom, left:right] = mixed.astype(np.float32)
    return finish_alpha(result)


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    return ~dilate(~mask, radius)


def key_backdrop(rgb: np.ndarray, alpha: np.ndarray, radius: int) -> np.ndarray:
    """Clear the old backdrop that shows between loose hair strands.

    Subject masks are solid around loose hair, so the wall between strands is
    kept and shows as a grey patch on a new red or blue background. Near the
    edge, each pixel is compared with the local backdrop ``B`` (pixels outside
    the mask) and the deep subject colour ``F`` (well inside it), like a chroma
    key: ``α = (C − B)·(F − B) / |F − B|²``. Only lowered, never raised, and
    only where subject and backdrop clearly differ.
    """
    outside = alpha <= 0.02
    if not outside.any() or outside.all():
        return alpha
    reach = radius * 8
    # Backdrop can hide deep inside a mop of hair, well away from the edge.
    band = dilate(outside, reach * 2) & ~outside
    rows, cols = np.nonzero(band)
    if not len(rows):
        return alpha
    pad = reach * 3
    top, left = max(0, rows.min() - pad), max(0, cols.min() - pad)
    bottom, right = min(alpha.shape[0], rows.max() + 1 + pad), min(alpha.shape[1], cols.max() + 1 + pad)
    a = alpha[top:bottom, left:right].astype(np.float64)
    colors = rgb[top:bottom, left:right].astype(np.float64)
    back_w = (a <= 0.02).astype(np.float64)
    deep_w = _erode(a >= 0.98, radius * 4).astype(np.float64)
    # Backdrop colour: nearby where there is some, else the whole backdrop's
    # average (ID-photo walls are plain enough for that).
    wide = reach * 3
    back_n = _box_mean(back_w, wide)
    deep_n = _box_mean(deep_w, reach * 2)
    local_back = np.dstack([_box_mean(colors[..., c] * back_w, wide) for c in range(3)]) / np.maximum(back_n, 1e-6)[..., None]
    overall = rgb[outside].reshape(-1, 3).astype(np.float64).mean(axis=0)
    near = np.clip(back_n / 0.05, 0.0, 1.0)[..., None]
    back = local_back * near + overall * (1.0 - near)
    fore = np.dstack([_box_mean(colors[..., c] * deep_w, reach * 2) for c in range(3)]) / np.maximum(deep_n, 1e-6)[..., None]
    span = fore - back
    length2 = np.einsum("...c,...c->...", span, span)
    t = np.einsum("...c,...c->...", colors - back, span) / np.maximum(length2, 1e-6)
    # Only pixels that really are a mix of backdrop and subject colour: skin,
    # lips or a coloured collar next to dark hair lie far off that line.
    residual = np.linalg.norm(colors - (back + np.clip(t, 0.0, 1.0)[..., None] * span), axis=-1)
    on_line = np.clip(1.0 - (residual - 6.0) / 10.0, 0.0, 1.0) * (t > -0.2)
    # Soften the key a little so strands stay continuous.
    keyed = np.clip((np.clip(t, 0.0, 1.0) - 0.08) / 0.6, 0.0, 1.0)
    trust = np.clip((np.sqrt(length2) - 45.0) / 45.0, 0.0, 1.0) * (deep_n > 0.02) * on_line
    local_band = band[top:bottom, left:right]
    lowered = np.minimum(a, trust * keyed + (1.0 - trust) * a)
    result = alpha.copy()
    result[top:bottom, left:right] = np.where(local_band, lowered, a).astype(np.float32)
    return result
