from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from wemute.engines.common import ConversionError, Reporter, last_line, remove_tree, run_tool, scratch_dir

TIMEOUT_SECONDS = 600
_PERCENT = re.compile(r"^\s*(\d{1,3})%\s")


def convert(
    ebook_convert: Path,
    source: Path,
    output: Path,
    extension: str,
    config_dir: Path,
    reporter: Reporter,
    source_suffix: str = "",
    timeout: float = TIMEOUT_SECONDS,
) -> None:
    """Run Calibre's ``ebook-convert``; it prints "NN% step" lines we turn into progress."""
    if not ebook_convert.is_file():
        raise reporter.error("tool_missing", name="Calibre")
    scratch = scratch_dir("ebook-")
    try:
        suffix = source_suffix or source.suffix.lower()
        staged = scratch / f"input{suffix}"
        # A copy, never a link: nothing Calibre does may reach the original.
        shutil.copyfile(source, staged)
        produced = scratch / f"output{extension}"
        command = [str(ebook_convert), str(staged), str(produced)]
        if extension == ".pdf":
            command += ["--paper-size", "a4", "--pdf-page-margin-left", "54",
                        "--pdf-page-margin-right", "54"]
        config_dir.mkdir(parents=True, exist_ok=True)
        env = {
            **os.environ,
            # Keep Calibre's settings away from a user's own Calibre library.
            "CALIBRE_CONFIG_DIRECTORY": str(config_dir),
            "CALIBRE_TEMP_DIR": str(scratch),
        }
        reporter.stage("stage_converting")

        def on_line(line: str) -> None:
            match = _PERCENT.match(line)
            if match:
                reporter.progress(min(99, int(match.group(1))) / 100)

        result = run_tool(
            command,
            timeout=timeout,
            timeout_message=reporter.text("tool_timeout", seconds=int(timeout)),
            cwd=scratch,
            env=env,
            on_line=on_line,
        )
        if "DRMError" in result.stdout:
            raise reporter.error("ebook_drm")
        if result.returncode != 0 or not produced.is_file():
            detail = last_line(result.stdout)
            message = reporter.text("ebook_failed")
            raise ConversionError(f"{message}: {detail}" if detail else message)
        reporter.stage("stage_saving")
        shutil.move(str(produced), str(output))
    finally:
        remove_tree(scratch)
