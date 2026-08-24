from __future__ import annotations

from wemute.app_info import AppInfoController, THIRD_PARTY_COMPONENTS


def test_app_info_exposes_current_version() -> None:
    assert AppInfoController().version == "0.3.1"


def test_third_party_rows_are_https_and_complete() -> None:
    assert len(THIRD_PARTY_COMPONENTS) >= 8
    for component in THIRD_PARTY_COMPONENTS:
        assert component["name"]
        assert component["version"]
        assert component["license"]
        assert component["url"].startswith("https://")
