#!/usr/bin/env python3
"""Refresh mlx-audio-io's RECORD after macOS code signing changes its binary."""

from __future__ import annotations

import base64
import csv
import hashlib
import sys
from pathlib import Path


def refresh(app: Path) -> None:
    resources = app / "Contents" / "Resources"
    records = list(resources.glob("mlx_audio_io-*.dist-info/RECORD"))
    extensions = list(resources.glob("mlx_audio_io/_core*.so"))
    if len(records) != 1 or len(extensions) != 1:
        raise RuntimeError(
            "Expected one mlx-audio-io RECORD and one native extension in the app."
        )
    record = records[0]
    extension = extensions[0].resolve()
    digest = base64.urlsafe_b64encode(
        hashlib.sha256(extension.read_bytes()).digest()
    ).decode("ascii").rstrip("=")
    member = f"mlx_audio_io/{extensions[0].name}"
    rows: list[list[str]] = []
    updated = False
    with record.open(newline="", encoding="utf-8") as source:
        for row in csv.reader(source):
            if row and row[0] == member:
                row = [member, f"sha256={digest}", str(extension.stat().st_size)]
                updated = True
            rows.append(row)
    if not updated:
        raise RuntimeError(f"The native extension is not declared in {record}.")
    with record.open("w", newline="", encoding="utf-8") as destination:
        csv.writer(destination, lineterminator="\n").writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: refresh-mlx-audio-record.py <Wemute.app>")
    refresh(Path(sys.argv[1]).resolve())
