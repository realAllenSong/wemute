"""Worker process for document-like conversions.

Usage: ``python -m wemute.convert_worker '<request json>'``. Progress lines on
stdout (``wemute_progress=``, ``wemute_stage=``, ``wemute_indeterminate=``);
on failure the last stderr line is the message shown to the user.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from wemute.engines import archive, data, ebook, font, office, pdf, vector
from wemute.engines.common import ConversionError, Reporter, install_signal_handlers, remove_tree, scratch_dir


def _office(request: dict, reporter: Reporter, source: Path, output: Path, extension: str) -> None:
    office.convert(
        Path(request["tools"]["libreoffice"]),
        source,
        output,
        extension,
        Path(request["office_profile"]),
        reporter,
        source_suffix=request["source_suffix"],
    )


def _vision(request: dict, reporter: Reporter) -> None:
    """Apple Vision and Core Image tools (macOS); imported only when used."""
    from wemute.engines import ocr, photo, scan

    tool = request["tool"]
    options = request.get("options", {})
    sources = [Path(value) for value in request["sources"]]
    output = Path(request["output"])
    extension = request["extension"]
    if tool == "ocr":
        target = options.get("format", "txt")
        if request.get("source_kind") == "pdf":
            ocr.pdf_ocr(sources[0], output, "pdf" if target == "pdf" else "txt", reporter)
        elif target == "pdf":
            ocr.images_to_searchable_pdf(sources, output, reporter)
        else:
            ocr.images_to_text(sources, output, target, reporter)
    elif tool == "scan":
        mode = options.get("mode", "color")
        if extension == ".pdf":
            scan.scan_to_pdf(sources, output, mode, reporter)
        else:
            scan.scan_to_image(sources[0], output, mode, reporter)
    elif tool == "codes":
        photo.codes_to_file(sources, output, extension == ".csv", reporter)
    elif tool == "triage":
        duplicates, blurry = photo.triage(sources, output, reporter)
        if duplicates or blurry:
            reporter.note("triage_found", duplicates=duplicates, blurry=blurry)
        else:
            reporter.note("triage_none")
    else:
        photo.run_photo_tool(tool, sources[0], output, extension, options, reporter)


def run(request: dict, reporter: Reporter) -> None:
    engine = request["engine"]
    if engine == "vision":
        _vision(request, reporter)
        return
    target = request["target"]
    sources = [Path(value) for value in request["sources"]]
    source = sources[0]
    output = Path(request["output"])
    suffix = request["source_suffix"]
    stem = request["stem"]
    extension = request.get("extension", "")

    if engine == "office":
        _office(request, reporter, source, output, extension)
    elif engine == "office_slides":
        scratch = scratch_dir("slides-")
        try:
            slides = scratch / "slides.pdf"
            _office(request, reporter, source, slides, ".pdf")
            pdf.render_pages(slides, output, "PNG", stem, reporter, (0.6, 1.0))
        finally:
            remove_tree(scratch)
    elif engine == "office_table":
        scratch = scratch_dir("sheet-")
        try:
            workbook = scratch / "workbook.xlsx"
            _office(request, reporter, source, workbook, ".xlsx")
            reporter.indeterminate(False)
            data.table_convert(workbook, ".xlsx", output, target, reporter, stem=stem)
        finally:
            remove_tree(scratch)
    elif engine == "table":
        data.table_convert(source, suffix, output, target, reporter, stem=stem)
    elif engine == "text":
        pandoc = request["tools"].get("pandoc")
        data.text_convert(source, suffix, output, target, reporter, Path(pandoc) if pandoc else None)
    elif engine == "pdf":
        if target == "DOCX":
            pdf.to_docx(source, output, reporter)
        elif target == "TXT":
            pdf.to_text(source, output, reporter)
        elif target == "Smaller PDF":
            pdf.compress(source, output, reporter)
        else:
            pdf.render_pages(source, output, request["image_format"], stem, reporter)
    elif engine == "ebook":
        ebook.convert(
            Path(request["tools"]["calibre"]),
            source,
            output,
            extension,
            Path(request["calibre_config"]),
            reporter,
            source_suffix=suffix,
        )
    elif engine == "archive":
        archive.extract(source, output, reporter, source_suffix=suffix)
    elif engine == "font":
        font.convert(source, output, extension, reporter)
    elif engine == "vector":
        vector.convert(source, output, extension, reporter)
    elif engine == "images_pdf":
        pdf.images_to_pdf(sources, output, reporter)
    elif engine == "merge_pdf":
        pdf.merge(sources, output, reporter)
    elif engine == "pack":
        archive.pack(sources, output, request["archive_format"], reporter)
    else:
        raise ConversionError(f"Unknown converter: {engine}")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: convert_worker '<request json>'", file=sys.stderr)
        return 2
    install_signal_handlers()
    request = json.loads(arguments[0])
    reporter = Reporter(request.get("language", "en"))
    try:
        run(request, reporter)
    except ConversionError as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1
    except Exception as exc:  # noqa: BLE001 - any failure is reported, never hangs
        traceback.print_exc(file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    output = Path(request["output"])
    if not output.exists():
        print("The converter did not produce an output.", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
