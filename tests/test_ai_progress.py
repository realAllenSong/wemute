from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from wemute.ai_worker import Reporter, estimate_fraction


def progress_values(events: list[dict[str, object]]) -> list[float]:
    return [float(event["value"]) for event in events if event["type"] == "progress"]


def test_estimate_curve_moves_smoothly_and_never_reaches_the_end() -> None:
    samples = [estimate_fraction(seconds / 10, 2.0) for seconds in range(0, 200)]

    assert samples[0] == 0.0
    assert samples == sorted(samples)
    assert 0.84 < estimate_fraction(2.0, 2.0) < 0.86
    assert estimate_fraction(60.0, 2.0) < 0.99


def test_heartbeat_keeps_progress_moving_during_a_silent_step() -> None:
    events: list[dict[str, object]] = []
    reporter = Reporter(events.append)
    reporter.interval = 0.05

    with reporter.estimate(0.2, 0.8, expected=0.4):
        time.sleep(0.5)

    values = progress_values(events)
    assert values[0] == 0.2
    assert values[-1] == 0.8
    assert values == sorted(values)
    assert len(values) >= 6
    assert all(later - earlier < 0.2 for earlier, later in zip(values, values[1:]))


def test_progress_is_monotonic_and_stage_events_carry_labels() -> None:
    events: list[dict[str, object]] = []
    reporter = Reporter(events.append)

    reporter.stage("prepare-first")
    reporter.progress(0.4)
    reporter.progress(0.3)
    reporter.stage("save")
    reporter.progress(1.0)

    assert progress_values(events) == [0.4, 1.0]
    stages = [event for event in events if event["type"] == "stage"]
    assert [event["stage"] for event in stages] == ["prepare-first", "save"]
    assert all(isinstance(event["label"], str) and event["label"] for event in stages)


def test_plain_callbacks_still_receive_fractions() -> None:
    received: list[float] = []
    reporter = Reporter.wrap(received.append)

    reporter.stage("process")
    reporter(0.5)
    reporter.progress(1.0)

    assert received == [0.5, 1.0]


@pytest.mark.skipif(not Path("/usr/bin/awk").is_file(), reason="needs /usr/bin/awk")
def test_out_of_process_ticker_reports_while_this_process_is_blocked(tmp_path: Path) -> None:
    script = tmp_path / "blocked.py"
    script.write_text(
        "import time\n"
        "from wemute.ai_worker import Reporter, _event, _ticker_line\n"
        "import sys\n"
        "reporter = Reporter(lambda p: _event(sys.stdout, {'job_id': 'job-9', **p}),\n"
        "                    _ticker_line(sys.stdout, 'job-9'))\n"
        "with reporter.estimate(0.1, 0.9, expected=1.0):\n"
        "    time.sleep(1.2)\n"
        "reporter.progress(1.0)\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=30, check=True
    )

    events = [
        json.loads(line.partition("=")[2])
        for line in completed.stdout.splitlines()
        if line.startswith("wemute_event=")
    ]
    values = [event["value"] for event in events]
    assert all(event["job_id"] == "job-9" and event["type"] == "progress" for event in events)
    assert len(values) >= 5  # about one line every 0.2 s from the ticker
    assert values == sorted(values)
    assert values[-1] == 1.0
