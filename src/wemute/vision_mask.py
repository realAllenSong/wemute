"""Apple Vision's subject cut-out (the one behind "Remove Background").

``VNGenerateForegroundInstanceMaskRequest`` (macOS 14+) finds every
foreground instance — people, pets, products — with clean hair edges. ID
photos and portrait background blur use the same mask, refined the same way.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def foreground_mask(image: Image.Image) -> np.ndarray | None:
    """Soft foreground mask (float32, 0–1) for every instance, at full resolution;
    None when Vision finds no subject."""
    import Quartz
    import Vision
    from Foundation import NSData

    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = NSData.dataWithBytes_length_(rgba.tobytes(), width * height * 4)
    provider = Quartz.CGDataProviderCreateWithCFData(data)
    color_space = Quartz.CGColorSpaceCreateWithName(Quartz.kCGColorSpaceSRGB)
    cg_image = Quartz.CGImageCreate(
        width,
        height,
        8,
        32,
        width * 4,
        color_space,
        Quartz.kCGImageAlphaNoneSkipLast,
        provider,
        None,
        False,
        Quartz.kCGRenderingIntentDefault,
    )
    request = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Apple Vision could not analyse the image: {error}")
    results = request.results() or []
    if not results:
        return None
    observation = results[0]
    instances = observation.allInstances()
    if instances is None or instances.count() == 0:
        return None
    buffer, error = observation.generateScaledMaskForImageForInstances_fromRequestHandler_error_(
        instances, handler, None
    )
    if buffer is None:
        raise RuntimeError(f"Apple Vision could not build the mask: {error}")
    Quartz.CVPixelBufferLockBaseAddress(buffer, Quartz.kCVPixelBufferLock_ReadOnly)
    try:
        mask_width = Quartz.CVPixelBufferGetWidth(buffer)
        mask_height = Quartz.CVPixelBufferGetHeight(buffer)
        row_bytes = Quartz.CVPixelBufferGetBytesPerRow(buffer)
        raw = Quartz.CVPixelBufferGetBaseAddress(buffer).as_buffer(row_bytes * mask_height)
        mask = (
            np.frombuffer(raw, dtype=np.float32)
            .reshape(mask_height, row_bytes // 4)[:, :mask_width]
            .copy()
        )
    finally:
        Quartz.CVPixelBufferUnlockBaseAddress(buffer, Quartz.kCVPixelBufferLock_ReadOnly)
    if (mask_width, mask_height) != (width, height):
        mask = np.asarray(
            Image.fromarray(mask, mode="F").resize((width, height), Image.Resampling.BICUBIC)
        )
    return np.clip(mask, 0.0, 1.0)


def refined_alpha(rgb: np.ndarray, mask: np.ndarray, key: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """The same edge refinement Remove Background uses: guided filter, then
    background colour taken out of the edge pixels. ``key`` also clears the
    old backdrop between loose hair strands (for a new solid background).
    Returns (alpha, colors)."""
    from wemute.mattes import decontaminate_edges, finish_alpha, guided_refine, key_backdrop

    radius = max(2, round(max(rgb.shape[1], rgb.shape[0]) / 300))
    alpha = finish_alpha(guided_refine(rgb, mask, radius))
    if key:
        alpha = key_backdrop(rgb, alpha, radius)
    colors = decontaminate_edges(rgb, alpha, radius)
    return alpha, colors
