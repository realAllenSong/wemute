from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

from wemute.engines.common import ConversionError, Reporter, last_line, run_tool

BSDTAR = Path("/usr/bin/bsdtar")
TIMEOUT_SECONDS = 1800
COMPOUND_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst")
# Already-compressed formats are stored, not deflated again.
STORED_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".avif",
    ".mp4", ".mov", ".mkv", ".webm", ".m4v", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac",
    ".zip", ".7z", ".rar", ".gz", ".tgz", ".bz2", ".xz", ".docx", ".xlsx", ".pptx", ".epub",
    ".woff", ".woff2", ".pdf",
}
_JUNK = {"__MACOSX", ".DS_Store"}


def archive_stem(path: Path) -> str:
    name = path.name
    lowered = name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if lowered.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _entry_count(source: Path) -> int:
    try:
        result = run_tool(
            [str(BSDTAR), "-tf", str(source)], timeout=120, timeout_message="list timeout"
        )
    except ConversionError:
        return 0
    if result.returncode != 0:
        return 0
    return sum(1 for line in result.stdout.splitlines() if line.strip())


def zip_name_charset(source: Path) -> str:
    """"CP936" when a ZIP stores GBK names without the UTF-8 flag (Windows, zh)."""
    try:
        with zipfile.ZipFile(source) as archive:
            raw = [
                info.filename.encode("cp437")
                for info in archive.infolist()
                if not info.flag_bits & 0x800
            ]
    except (OSError, zipfile.BadZipFile, UnicodeEncodeError, ValueError):
        return ""
    non_ascii = [name for name in raw if any(byte > 127 for byte in name)]
    if not non_ascii:
        return ""
    try:
        for name in non_ascii:
            name.decode("utf-8")
        return ""
    except UnicodeDecodeError:
        pass
    try:
        for name in non_ascii:
            name.decode("gbk")
        return "CP936"
    except UnicodeDecodeError:
        return ""


def _with_bsdtar(source: Path, folder: Path, reporter: Reporter, suffix: str) -> None:
    total = _entry_count(source)
    options: list[str] = []
    if suffix == ".zip" and (charset := zip_name_charset(source)):
        options = ["--options", f"zip:hdrcharset={charset}"]
    done = 0

    def on_line(line: str) -> None:
        nonlocal done
        if line.startswith("x "):
            done += 1
            if total:
                reporter.progress(min(0.95, done / total))

    # bsdtar refuses absolute paths and ".." members unless -P is given.
    result = run_tool(
        [
            str(BSDTAR),
            "-x",
            "-v",
            "-f",
            str(source),
            "-C",
            str(folder),
            "--no-same-owner",
            "--no-mac-metadata",
            "--exclude",
            "__MACOSX",
            "--exclude",
            "*/.DS_Store",
            "--exclude",
            ".DS_Store",
            *options,
        ],
        timeout=TIMEOUT_SECONDS,
        timeout_message=reporter.text("tool_timeout", seconds=TIMEOUT_SECONDS),
        env={**os.environ, "LC_ALL": "en_US.UTF-8"},
        on_line=on_line,
    )
    if result.returncode != 0:
        output = result.stdout.lower()
        if "passphrase" in output or "encrypt" in output or "password" in output:
            raise reporter.error("encrypted_archive")
        detail = last_line(result.stdout)
        message = reporter.text("archive_failed")
        raise ConversionError(f"{message}: {detail}" if detail else message)


def _with_py7zr(source: Path, folder: Path, reporter: Reporter) -> None:
    import py7zr

    try:
        with py7zr.SevenZipFile(source) as archive:
            if archive.needs_password():
                raise reporter.error("encrypted_archive")
            archive.extractall(path=folder)
    except py7zr.exceptions.PasswordRequired as exc:
        raise reporter.error("encrypted_archive") from exc
    except (py7zr.exceptions.Bad7zFile, OSError) as exc:
        raise ConversionError(f"{reporter.text('archive_failed')}: {exc}") from exc


def extract(source: Path, folder: Path, reporter: Reporter, source_suffix: str = "") -> None:
    """Extract into ``folder`` (created). A lone top-level folder is unwrapped."""
    folder.mkdir(parents=True)
    reporter.stage("stage_extracting")
    suffix = source_suffix or source.suffix.lower()
    try:
        _with_bsdtar(source, folder, reporter, suffix)
    except ConversionError:
        if suffix != ".7z":
            raise
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        _with_py7zr(source, folder, reporter)
    entries = [entry for entry in folder.iterdir() if entry.name not in _JUNK]
    for junk in folder.iterdir():
        if junk.name in _JUNK:
            shutil.rmtree(junk, ignore_errors=True) if junk.is_dir() else junk.unlink()
    if not entries:
        raise reporter.error("empty_archive")
    if len(entries) == 1 and entries[0].is_dir() and not entries[0].is_symlink():
        # "photos.zip" holding "photos/…" becomes one folder, not two.
        inner = entries[0]
        staging = folder.with_name(folder.name + ".unwrap")
        os.rename(inner, staging)
        folder.rmdir()
        os.rename(staging, folder)
    reporter.progress(1.0)


def _arc_names(sources: list[Path]) -> list[str]:
    used: set[str] = set()
    names: list[str] = []
    for source in sources:
        candidate = source.name
        number = 2
        while candidate.lower() in used:
            candidate = f"{source.stem} {number}{source.suffix}"
            number += 1
        used.add(candidate.lower())
        names.append(candidate)
    return names


def pack(sources: list[Path], output: Path, archive_format: str, reporter: Reporter) -> None:
    """Pack files flat into one ZIP or 7Z, in list order; same names get a number."""
    reporter.stage("stage_packing")
    names = _arc_names(sources)
    total = sum(max(1, source.stat().st_size) for source in sources)
    written = 0
    if archive_format == "7z":
        import py7zr

        with py7zr.SevenZipFile(output, "w") as archive:
            for source, name in zip(sources, names):
                archive.write(source, name)
                written += max(1, source.stat().st_size)
                reporter.progress(0.98 * written / total)
        reporter.progress(1.0)
        return
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        for source, name in zip(sources, names):
            stored = source.suffix.lower() in STORED_SUFFIXES
            info = zipfile.ZipInfo.from_file(source, name)
            info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
            with source.open("rb") as handle, archive.open(info, "w") as target:
                while chunk := handle.read(1024 * 1024):
                    target.write(chunk)
                    written += len(chunk)
                    reporter.progress(0.98 * written / total)
    reporter.progress(1.0)
