from __future__ import annotations

import json
from pathlib import Path

from wemute.actions import ACTIONS, availability, menu_tree, search, text
from wemute.capabilities import set_output_tag, unique_output_path
from wemute.domain import OperationKind
from wemute.preferences import PreferenceStore, Preferences, resolve_dark

EVERYTHING = availability(set(OperationKind), vision=True, updater=True)


def _first(query: str, language: str) -> str:
    results = search(query, language, EVERYTHING)
    assert results, f"no result for {query!r}"
    return text(results[0].palette_title or results[0].title, language)


def test_palette_finds_actions_in_both_languages() -> None:
    assert "PDF" in _first("转 pdf", "zh")
    assert "去背景" in _first("去背景", "zh")
    assert "OCR" in _first("ocr", "zh") or "文字" in _first("ocr", "zh")
    assert "background" in _first("remove background", "en").lower()
    assert search("heic", "en", EVERYTHING)


def test_palette_hides_actions_this_mac_cannot_offer() -> None:
    no_vision = availability(set(), vision=False, updater=False)
    hidden = {action.id for action in ACTIONS if no_vision(action) == "hidden"}
    assert hidden, "Vision tools should be hidden without Vision"
    for query in ("ocr", "扫描", "证件照"):
        assert not hidden & {action.id for action in search(query, "zh", no_vision)}


def test_menu_tree_has_headers_and_actions() -> None:
    rows = menu_tree("zh", EVERYTHING)
    types = {row["type"] for row in rows}
    assert {"header", "action"} <= types


def test_preferences_round_trip_and_reject_garbage(tmp_path: Path) -> None:
    store = PreferenceStore(tmp_path / "settings.json")
    assert store.load() == Preferences()
    store.save(Preferences(appearance="dark", reduce_motion=True, restore_session=False))
    assert store.load().appearance == "dark"
    assert store.load().reduce_motion is True
    assert store.load().restore_session is False
    (tmp_path / "settings.json").write_text(json.dumps({"appearance": "neon", "windows": {"a": [1, 2]}}))
    loaded = store.load()
    assert loaded.appearance == "system"
    assert loaded.windows == {}


def test_resolve_dark_follows_override_then_system() -> None:
    assert resolve_dark("dark", False) is True
    assert resolve_dark("light", True) is False
    assert resolve_dark("system", True) is True
    assert resolve_dark("system", False) is False


def test_output_tag_is_appended_to_output_names(tmp_path: Path) -> None:
    source = tmp_path / "IMG_0412.heic"
    source.write_bytes(b"x")
    try:
        set_output_tag("-wemute")
        assert unique_output_path(source, tmp_path, ".jpg").name == "IMG_0412-wemute.jpg"
        # Same format: the tag already keeps it apart from the original.
        same = tmp_path / "photo.jpg"
        same.write_bytes(b"x")
        assert unique_output_path(same, tmp_path, ".jpg").name == "photo-wemute.jpg"
    finally:
        set_output_tag("")
    assert unique_output_path(source, tmp_path, ".jpg").name == "IMG_0412.jpg"
