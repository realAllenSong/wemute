from __future__ import annotations

import os
import shutil
from pathlib import Path

from wemute.engines.common import ConversionError, Reporter, last_line, remove_tree, run_tool, scratch_dir
from wemute.engines.data import html_to_text

TIMEOUT_SECONDS = 300

# LibreOffice export filters by output extension. PDF picks the right
# component (Writer/Calc/Impress) from the document itself.
EXPORT_FILTERS = {
    ".pdf": "pdf",
    ".docx": "docx:MS Word 2007 XML",
    ".odt": "odt",
    ".rtf": "rtf:Rich Text Format",
    ".html": 'html:HTML (StarWriter):{"EmbedImages":{"type":"boolean","value":"true"}}',
    ".xlsx": "xlsx:Calc MS Excel 2007 XML",
    ".ods": "ods",
    ".pptx": "pptx:Impress MS PowerPoint 2007 XML",
    ".odp": "odp",
}

# UTF-8 (76), comma or tab separated, first line as text.
_CSV_IMPORT = {".csv": "CSV:44,34,76,1", ".tsv": "CSV:9,34,76,1"}


def convert(
    soffice: Path,
    source: Path,
    output: Path,
    extension: str,
    profile: Path,
    reporter: Reporter,
    timeout: float = TIMEOUT_SECONDS,
    source_suffix: str = "",
) -> None:
    """Convert ``source`` with headless LibreOffice and move the result to ``output``."""
    if not soffice.is_file():
        raise reporter.error("tool_missing", name="LibreOffice")
    scratch = scratch_dir("office-")
    try:
        profile.mkdir(parents=True, exist_ok=True)
        if not any(profile.iterdir()):
            reporter.stage("stage_starting_office")
        else:
            reporter.stage("stage_converting")
        reporter.indeterminate(True)
        # LibreOffice picks the import filter from the name and names its
        # output after the input; stage a copy whose suffix states the format.
        suffix = source_suffix or source.suffix.lower()
        stem = source.stem if source.suffix.lower() == suffix else source.name
        staged = scratch / f"{stem}{suffix}"
        # A copy, never a link: nothing LibreOffice does may reach the original.
        shutil.copyfile(source, staged)
        outdir = scratch / "out"
        outdir.mkdir()
        command = [
            str(soffice),
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--headless",
            "--invisible",
            "--norestore",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
        ]
        if suffix in _CSV_IMPORT:
            command.append(f"--infilter={_CSV_IMPORT[suffix]}")
        # Headless text export never returns in LibreOffice 26.8 on macOS;
        # go through plain HTML and flatten that instead.
        export = ".html" if extension == ".txt" else extension
        export_filter = "html:HTML (StarWriter)" if extension == ".txt" else EXPORT_FILTERS[extension]
        command += ["--convert-to", export_filter, "--outdir", str(outdir), str(staged)]
        result = run_tool(
            command,
            timeout=timeout,
            timeout_message=reporter.text("office_timeout", seconds=int(timeout)),
            cwd=scratch,
            env={**os.environ, "SAL_USE_VCLPLUGIN": "svp"},
        )
        produced = outdir / f"{stem}{export}"
        if not produced.is_file() or produced.stat().st_size == 0:
            detail = last_line(result.stdout)
            message = reporter.text("office_failed")
            raise ConversionError(f"{message}: {detail}" if detail else message)
        reporter.stage("stage_saving")
        if export != extension:
            markup = produced.read_text(encoding="utf-8", errors="replace")
            output.write_text(html_to_text(markup), encoding="utf-8")
        else:
            shutil.move(str(produced), str(output))
    finally:
        remove_tree(scratch)
