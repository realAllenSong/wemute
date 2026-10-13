"""Image loading and saving for the Vision / Core Image tools.

Pixels travel as Pillow images, oriented the right way up. The source colour
profile rides along untouched: Core Image and Vision see the pixels tagged as
sRGB, which round-trips them unchanged, and outputs embed the original profile.
"""

from __future__ import annotations

import io
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from wemute.engines.common import ConversionError, Reporter
from wemute.native_images import HEIC_SUFFIXES, encode_heic

# Outputs keep the source format when it can carry full-quality pixels.
KEEP_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}
_EXIF_ORIENTATION = 0x0112
_EXIF_GPS = 0x8825
_EXIF_IFD = 0x8769
_EXIF_ISO = 0x8827


@dataclass
class Photo:
    image: Image.Image
    icc: bytes | None = None
    exif: bytes | None = None
    iso: int | None = None
    name: str = ""
    info: dict = field(default_factory=dict)

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size


def photo_extension(suffix: str) -> str:
    suffix = suffix.lower()
    return suffix if suffix in KEEP_SUFFIXES else ".png"


def _exif_details(image: Image.Image) -> tuple[bytes | None, int | None]:
    try:
        exif = image.getexif()
    except Exception:  # noqa: BLE001 - damaged EXIF must not block the photo
        return None, None
    if not exif:
        return None, None
    iso = None
    try:
        value = exif.get_ifd(_EXIF_IFD).get(_EXIF_ISO)
        if isinstance(value, (tuple, list)):
            value = value[0] if value else None
        iso = int(value) if value else None
    except Exception:  # noqa: BLE001
        iso = None
    exif[_EXIF_ORIENTATION] = 1
    try:
        return exif.tobytes(), iso
    except Exception:  # noqa: BLE001
        return None, iso


def _load_with_image_io(path: Path) -> tuple[Image.Image, bytes | None]:
    """HEIC/HEIF (and anything Pillow cannot read) through ImageIO, oriented."""
    import Quartz
    from Foundation import NSURL

    source = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(path)), None)
    if source is None or Quartz.CGImageSourceGetCount(source) == 0:
        raise OSError("ImageIO cannot read this file")
    properties = Quartz.CGImageSourceCopyPropertiesAtIndex(source, 0, None) or {}
    width = int(properties.get(Quartz.kCGImagePropertyPixelWidth, 0))
    height = int(properties.get(Quartz.kCGImagePropertyPixelHeight, 0))
    options = {
        Quartz.kCGImageSourceCreateThumbnailFromImageAlways: True,
        Quartz.kCGImageSourceCreateThumbnailWithTransform: True,
        Quartz.kCGImageSourceThumbnailMaxPixelSize: max(width, height, 1),
        Quartz.kCGImageSourceShouldCacheImmediately: True,
    }
    cg_image = Quartz.CGImageSourceCreateThumbnailAtIndex(source, 0, options)
    if cg_image is None:
        raise OSError("ImageIO cannot decode this file")
    color_space = Quartz.CGImageGetColorSpace(cg_image)
    icc = None
    if color_space is not None and Quartz.CGColorSpaceGetModel(color_space) == Quartz.kCGColorSpaceModelRGB:
        data = Quartz.CGColorSpaceCopyICCData(color_space)
        icc = bytes(data) if data else None
    else:
        color_space = None
    return cgimage_to_pil(cg_image, color_space), icc


def load_photo(path: Path, reporter: Reporter | None = None) -> Photo:
    """Full-resolution pixels the right way up, with ICC and EXIF kept aside."""
    path = Path(path)
    try:
        if path.suffix.lower() in HEIC_SUFFIXES:
            image, icc = _load_with_image_io(path)
            exif, iso = None, None
            try:
                with Image.open(path) as opened:  # pillow-heif may be absent; best effort
                    exif, iso = _exif_details(opened)
            except Exception:  # noqa: BLE001
                pass
            return Photo(image, icc, exif, iso, path.name)
        with Image.open(path) as opened:
            opened.load()
            exif, iso = _exif_details(opened)
            icc = opened.info.get("icc_profile")
            if getattr(opened, "is_animated", False):
                opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            has_alpha = image.mode in {"RGBA", "LA", "PA"} or (
                image.mode == "P" and "transparency" in image.info
            )
            image = image.convert("RGBA" if has_alpha else "RGB")
            return Photo(image, icc, exif, iso, path.name)
    except (OSError, ValueError, Image.DecompressionBombError):
        try:
            image, icc = _load_with_image_io(path)
            return Photo(image, icc, None, None, path.name)
        except Exception as exc:  # noqa: BLE001
            message = (
                reporter.text("bad_image", name=path.name) if reporter else f"Could not read image: {path.name}"
            )
            raise ConversionError(message) from exc


def flatten(image: Image.Image, color: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    if image.mode != "RGBA":
        return image.convert("RGB")
    background = Image.new("RGB", image.size, color)
    background.paste(image, mask=image.getchannel("A"))
    return background


def save_photo(
    image: Image.Image,
    output: Path,
    photo: Photo,
    *,
    extension: str | None = None,
    quality: int = 92,
    strip_location: bool = False,
) -> None:
    """Write at full quality in the output's format, with the source profile."""
    extension = (extension or output.suffix).lower()
    output.parent.mkdir(parents=True, exist_ok=True)
    exif = photo.exif
    if exif and strip_location:
        try:
            parsed = Image.Exif()
            parsed.load(exif)
            parsed.pop(_EXIF_GPS, None)
            exif = parsed.tobytes()
        except Exception:  # noqa: BLE001
            exif = None
    options: dict[str, object] = {}
    if photo.icc:
        options["icc_profile"] = photo.icc
    if extension in {".jpg", ".jpeg"}:
        if exif:
            options["exif"] = exif
        flatten(image).save(output, "JPEG", quality=quality, subsampling=0, optimize=True, **options)
    elif extension == ".png":
        if exif:
            options["exif"] = exif
        image.save(output, "PNG", compress_level=6, **options)
    elif extension == ".webp":
        if exif:
            options["exif"] = exif
        image.save(output, "WEBP", quality=quality, method=5, **options)
    elif extension in {".tif", ".tiff"}:
        image.save(output, "TIFF", compression="tiff_lzw", **options)
    elif extension in HEIC_SUFFIXES:
        with tempfile.TemporaryDirectory(prefix="wemute-heic-out-") as scratch:
            staged = Path(scratch) / "staged.png"
            image.save(staged, "PNG", compress_level=1, **options)
            encoded = Path(scratch) / f"encoded{extension}"
            encode_heic(staged, encoded, quality)
            shutil.move(str(encoded), str(output))
    else:
        image.save(output, "PNG", **options)


def jpeg_bytes(image: Image.Image, quality: int = 90, icc: bytes | None = None) -> bytes:
    buffer = io.BytesIO()
    options = {"icc_profile": icc} if icc else {}
    image.save(buffer, "JPEG", quality=quality, optimize=True, **options)
    return buffer.getvalue()


# ── Core Graphics / Core Image bridges ───────────────────────────────────


def pil_to_cgimage(image: Image.Image):  # noqa: ANN201 - CGImageRef
    import Quartz
    from Foundation import NSData

    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = NSData.dataWithBytes_length_(rgba.tobytes(), width * height * 4)
    provider = Quartz.CGDataProviderCreateWithCFData(data)
    color_space = Quartz.CGColorSpaceCreateWithName(Quartz.kCGColorSpaceSRGB)
    alpha = (
        Quartz.kCGImageAlphaLast if image.mode == "RGBA" else Quartz.kCGImageAlphaNoneSkipLast
    )
    return Quartz.CGImageCreate(
        width, height, 8, 32, width * 4, color_space, alpha, provider, None, False,
        Quartz.kCGRenderingIntentDefault,
    )


def cgimage_to_pil(cg_image, color_space=None, alpha: bool = False) -> Image.Image:  # noqa: ANN001
    """Draw a CGImage into an RGBA bitmap (in its own colour space when given)."""
    import Quartz

    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)
    space = color_space or Quartz.CGColorSpaceCreateWithName(Quartz.kCGColorSpaceSRGB)
    context = Quartz.CGBitmapContextCreate(
        None, width, height, 8, width * 4, space, Quartz.kCGImageAlphaPremultipliedLast
    )
    Quartz.CGContextDrawImage(context, Quartz.CGRectMake(0, 0, width, height), cg_image)
    rendered = Quartz.CGBitmapContextCreateImage(context)
    row_bytes = Quartz.CGImageGetBytesPerRow(rendered)
    raw = bytes(Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(rendered)))
    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, row_bytes)[:, : width * 4]
    pixels = pixels.reshape(height, width, 4)
    image = Image.fromarray(np.ascontiguousarray(pixels), "RGBA")
    if alpha and int(pixels[..., 3].min()) < 255:
        return image
    return image.convert("RGB")


def ci_image(image: Image.Image):  # noqa: ANN201 - CIImage
    import Quartz

    return Quartz.CIImage.imageWithCGImage_(pil_to_cgimage(image))


_CONTEXT = None


def ci_context():  # noqa: ANN201
    global _CONTEXT
    if _CONTEXT is None:
        import Quartz

        _CONTEXT = Quartz.CIContext.contextWithOptions_(
            {Quartz.kCIContextUseSoftwareRenderer: False}
        )
    return _CONTEXT


def render_ci(image, extent=None) -> Image.Image:  # noqa: ANN001
    """Render a CIImage to an 8-bit RGB(A) Pillow image."""
    rect = extent if extent is not None else image.extent()
    cg_image = ci_context().createCGImage_fromRect_(image, rect)
    if cg_image is None:
        raise ConversionError("Core Image could not render the result")
    return cgimage_to_pil(cg_image)


def perform(cg_image, requests: list):  # noqa: ANN001, ANN201
    """Run Vision requests on one image; returns the handler for follow-up calls."""
    import Vision

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
    ok, error = handler.performRequests_error_(requests, None)
    if not ok:
        detail = error.localizedDescription() if error is not None else "unknown error"
        raise ConversionError(f"Apple Vision could not analyse the image: {detail}")
    return handler


def pixel_buffer_array(buffer) -> np.ndarray:  # noqa: ANN001
    """A one-channel CVPixelBuffer (8-bit or float) as float32 0–1, row 0 at the top."""
    import Quartz

    Quartz.CVPixelBufferLockBaseAddress(buffer, Quartz.kCVPixelBufferLock_ReadOnly)
    try:
        width = Quartz.CVPixelBufferGetWidth(buffer)
        height = Quartz.CVPixelBufferGetHeight(buffer)
        row_bytes = Quartz.CVPixelBufferGetBytesPerRow(buffer)
        raw = Quartz.CVPixelBufferGetBaseAddress(buffer).as_buffer(row_bytes * height)
        if Quartz.CVPixelBufferGetPixelFormatType(buffer) == Quartz.kCVPixelFormatType_OneComponent8:
            values = np.frombuffer(raw, dtype=np.uint8).reshape(height, row_bytes)[:, :width]
            return values.astype(np.float32) / 255.0
        values = np.frombuffer(raw, dtype=np.float32).reshape(height, row_bytes // 4)[:, :width]
        return values.copy()
    finally:
        Quartz.CVPixelBufferUnlockBaseAddress(buffer, Quartz.kCVPixelBufferLock_ReadOnly)


def resize_mask(values: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    if (values.shape[1], values.shape[0]) == size:
        return values
    image = Image.fromarray(values.astype(np.float32), mode="F")
    return np.asarray(image.resize(size, Image.Resampling.BICUBIC), dtype=np.float32)


def normalized_rect(box, width: int, height: int) -> tuple[float, float, float, float]:  # noqa: ANN001
    """A Vision bounding box (normalised, origin bottom-left) in pixels: x0, y0, x1, y1, origin top-left."""
    x0 = float(box.origin.x) * width
    x1 = x0 + float(box.size.width) * width
    y1 = (1 - float(box.origin.y)) * height
    y0 = y1 - float(box.size.height) * height
    return x0, y0, x1, y1


def ci_filter(name: str, **values):  # noqa: ANN003, ANN201
    import Quartz

    item = Quartz.CIFilter.filterWithName_(name)
    if item is None:
        raise ConversionError(f"Core Image filter {name} is not available on this Mac")
    item.setDefaults()
    for key, value in values.items():
        item.setValue_forKey_(value, key)
    return item
