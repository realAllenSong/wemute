from __future__ import annotations

import json
import os
from pathlib import Path

from wemute.domain import JobRecord
from wemute.paths import DATA_ROOT


class QueueStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (DATA_ROOT / "queue.json")

    def load(self) -> list[JobRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            jobs = [JobRecord.from_dict(item) for item in payload.get("jobs", [])]
            return [job for job in jobs if Path(job.source.path).exists()]
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def save(self, jobs: list[JobRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = {"version": 1, "jobs": [job.to_dict() for job in jobs]}
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.path)
