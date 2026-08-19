from __future__ import annotations

from wemute.updater import SparkleUpdater


def test_sparkle_updater_stays_disabled_in_development_process() -> None:
    updater = SparkleUpdater()
    assert updater.available is False
    updater.shutdown()
