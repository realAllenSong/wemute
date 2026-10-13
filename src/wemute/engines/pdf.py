from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path

from wemute.engines.common import ConversionError, Reporter

RENDER_DPI = 150


def _open_pdfium(source: Path, reporter: Reporter):  # noqa: ANN202
    import pypdfium2 as pdfium

    try:
        return pdfium.PdfDocument(str(source))
    except pdfium.PdfiumError as exc:
        if "password" in str(exc).lower():
            raise reporter.error("encrypted_pdf") from exc
        raise reporter.error("bad_pdf") from exc


def page_name(stem: str, index: int, count: int, extension: str) -> str:
    width = max(2, len(str(count)))
    return f"{stem} {index + 1:0{width}d}{extension}"


def render_pages(
    source: Path,
    folder: Path,
    image_format: str,
    stem: str,
    reporter: Reporter,
    progress_span: tuple[float, float] = (0.0, 1.0),
) -> int:
    """Write one PNG/JPEG per page into ``folder``; returns the page count."""
    document = _open_pdfium(source, reporter)
    folder.mkdir(parents=True, exist_ok=True)
    extension = ".jpg" if image_format == "JPEG" else ".png"
    count = len(document)
    if not count:
        raise reporter.error("no_pages")
    start, end = progress_span
    reporter.stage("stage_rendering")
    try:
        for index in range(count):
            page = document[index]
            image = page.render(scale=RENDER_DPI / 72).to_pil()
            target = folder / page_name(stem, index, count, extension)
            if image_format == "JPEG":
                image.convert("RGB").save(target, "JPEG", quality=90, optimize=True)
            else:
                image.save(target, "PNG", optimize=False)
            page.close()
            reporter.progress(start + (end - start) * (index + 1) / count)
    finally:
        document.close()
    return count


def to_text(source: Path, output: Path, reporter: Reporter) -> None:
    document = _open_pdfium(source, reporter)
    count = len(document)
    parts: list[str] = []
    try:
        for index in range(count):
            page = document[index]
            textpage = page.get_textpage()
            parts.append(textpage.get_text_range().replace("\r\n", "\n").rstrip())
            textpage.close()
            page.close()
            reporter.progress((index + 1) / max(1, count))
    finally:
        document.close()
    output.write_text("\n\n\f".join(parts).strip() + "\n", encoding="utf-8")


class _PageProgress(logging.Handler):
    """pdf2docx logs "(i/n) Page p" while parsing, then again while writing."""

    def __init__(self, reporter: Reporter) -> None:
        super().__init__(logging.INFO)
        self.reporter = reporter
        self.phase = 0

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "[3/4]" in message:
            self.phase = 1
        elif "[4/4]" in message:
            self.phase = 2
            self.reporter.stage("stage_saving")
        elif message.startswith("(") and record.args and len(record.args) >= 2:
            done, total = int(record.args[0]), max(1, int(record.args[1]))
            base = 0.05 if self.phase <= 1 else 0.6
            span = 0.55 if self.phase <= 1 else 0.38
            self.reporter.progress(base + span * done / total)


def to_docx(source: Path, output: Path, reporter: Reporter) -> None:
    import pikepdf

    try:
        with pikepdf.open(source):
            pass
    except pikepdf.PasswordError as exc:
        raise reporter.error("encrypted_pdf") from exc
    except pikepdf.PdfError as exc:
        raise reporter.error("bad_pdf") from exc
    from pdf2docx import Converter

    reporter.stage("stage_converting")
    handler = _PageProgress(reporter)
    root = logging.getLogger()
    previous = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        converter = Converter(str(source))
        try:
            converter.convert(str(output), multi_processing=False)
        finally:
            converter.close()
    except ConversionError:
        raise
    except Exception as exc:  # pdf2docx raises bare exceptions for odd layouts
        raise ConversionError(f"{reporter.text('bad_pdf')}: {exc}") from exc
    finally:
        root.removeHandler(handler)
        root.setLevel(previous)
    if not output.is_file():
        raise reporter.error("bad_pdf")


def compress(source: Path, output: Path, reporter: Reporter, max_edge: int = 2000, quality: int = 70) -> None:
    """Downsample and re-encode large images, then rewrite with compressed streams."""
    import pikepdf
    from PIL import Image
    from pikepdf import Name, PdfImage

    try:
        pdf = pikepdf.open(source)
    except pikepdf.PasswordError as exc:
        raise reporter.error("encrypted_pdf") from exc
    except pikepdf.PdfError as exc:
        raise reporter.error("bad_pdf") from exc
    reporter.stage("stage_compressing")
    with pdf:
        images = [
            obj
            for obj in pdf.objects
            if isinstance(obj, pikepdf.Stream) and obj.get("/Subtype") == Name.Image
        ]
        for index, stream in enumerate(images):
            reporter.progress(0.9 * index / max(1, len(images)))
            try:
                if stream.get("/ImageMask") or int(stream.get("/BitsPerComponent", 8)) != 8:
                    continue
                if "/SMask" in stream and stream.get("/Filter") != Name.DCTDecode:
                    # Keep lossless images with transparency untouched.
                    continue
                pdf_image = PdfImage(stream)
                if pdf_image.colorspace not in {"/DeviceRGB", "/DeviceGray", "/ICCBased"}:
                    continue
                image = pdf_image.as_pil_image()
                if image.mode not in {"RGB", "L"}:
                    continue
                if max(image.size) > max_edge:
                    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                image.save(buffer, "JPEG", quality=quality, optimize=True)
                data = buffer.getvalue()
                if len(data) >= len(stream.read_raw_bytes()):
                    continue
                stream.write(data, filter=Name.DCTDecode)
                stream.Width, stream.Height = image.size
                stream.ColorSpace = Name.DeviceRGB if image.mode == "RGB" else Name.DeviceGray
                stream.BitsPerComponent = 8
                for key in ("/DecodeParms", "/Decode"):
                    if key in stream:
                        del stream[key]
            except Exception:  # noqa: BLE001 - leave any image we cannot safely rewrite
                continue
        reporter.stage("stage_saving")
        pdf.remove_unreferenced_resources()
        pdf.save(
            output,
            compress_streams=True,
            recompress_flate=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
    reporter.progress(1.0)


def merge(sources: list[Path], output: Path, reporter: Reporter) -> None:
    import pikepdf

    reporter.stage("stage_packing")
    merged = pikepdf.Pdf.new()
    opened: list[pikepdf.Pdf] = []
    try:
        for index, source in enumerate(sources):
            try:
                document = pikepdf.open(source)
            except pikepdf.PasswordError as exc:
                raise ConversionError(f"{reporter.text('encrypted_pdf')}: {source.name}") from exc
            except pikepdf.PdfError as exc:
                raise ConversionError(f"{reporter.text('bad_pdf')}: {source.name}") from exc
            opened.append(document)
            merged.pages.extend(document.pages)
            reporter.progress(0.8 * (index + 1) / len(sources))
        reporter.stage("stage_saving")
        merged.save(output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    finally:
        for document in opened:
            document.close()
    reporter.progress(1.0)


_LOSSLESS = {".png", ".tif", ".tiff", ".bmp", ".gif"}
A4_LONG_EDGE_POINTS = 842.0


def _image_page_stream(source: Path, scratch: Path, index: int, reporter: Reporter):  # noqa: ANN202
    """Encoded pixels for one page: (data, filter, width, height, colorspace)."""
    import zlib

    from PIL import Image, ImageOps

    from wemute.native_images import HEIC_SUFFIXES, decode_heic

    path = source
    if source.suffix.lower() in HEIC_SUFFIXES:
        path = scratch / f"{index}.png"
        decode_heic(source, path)
    try:
        with Image.open(path) as opened:
            orientation = opened.getexif().get(0x0112, 1)
            if (
                opened.format == "JPEG"
                and orientation in (0, 1)
                and opened.mode in {"RGB", "L"}
            ):
                # Already a JPEG the right way up: embed the original bytes.
                colorspace = "/DeviceRGB" if opened.mode == "RGB" else "/DeviceGray"
                return path.read_bytes(), "/DCTDecode", opened.width, opened.height, colorspace
            image = ImageOps.exif_transpose(opened)
            if image.mode in {"RGBA", "LA", "P", "PA"}:
                rgba = image.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.getchannel("A"))
                image = flat
            elif image.mode != "L":
                image = image.convert("RGB")
            colorspace = "/DeviceRGB" if image.mode == "RGB" else "/DeviceGray"
            if source.suffix.lower() in _LOSSLESS:
                return zlib.compress(image.tobytes(), 6), "/FlateDecode", *image.size, colorspace
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=92, optimize=True)
            return buffer.getvalue(), "/DCTDecode", *image.size, colorspace
    except (OSError, ValueError) as exc:
        raise reporter.error("bad_image", name=source.name) from exc


def images_to_pdf(sources: list[Path], output: Path, reporter: Reporter) -> None:
    """One page per image in list order, each page's long edge at A4 height."""
    import pikepdf
    from pikepdf import Array, Dictionary, Name

    pdf = pikepdf.Pdf.new()
    reporter.stage("stage_reading")
    with tempfile.TemporaryDirectory(prefix="wemute-pdf-") as scratch:
        for index, source in enumerate(sources):
            data, filter_name, width, height, colorspace = _image_page_stream(
                source, Path(scratch), index, reporter
            )
            scale = A4_LONG_EDGE_POINTS / max(width, height)
            page_width, page_height = round(width * scale, 2), round(height * scale, 2)
            image = pikepdf.Stream(pdf, data)
            image.Type = Name.XObject
            image.Subtype = Name.Image
            image.Width = width
            image.Height = height
            image.ColorSpace = Name(colorspace)
            image.BitsPerComponent = 8
            image.Filter = Name(filter_name)
            content = pikepdf.Stream(
                pdf, f"q {page_width} 0 0 {page_height} 0 0 cm /Im0 Do Q".encode("ascii")
            )
            page = Dictionary(
                Type=Name.Page,
                MediaBox=Array([0, 0, page_width, page_height]),
                Resources=Dictionary(XObject=Dictionary(Im0=image)),
                Contents=content,
            )
            pdf.pages.append(pikepdf.Page(page))
            reporter.progress(0.9 * (index + 1) / len(sources))
    if not len(pdf.pages):
        raise reporter.error("no_pages")
    reporter.stage("stage_saving")
    pdf.save(output, compress_streams=True)
    reporter.progress(1.0)
