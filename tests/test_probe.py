from pathlib import Path

from PIL import Image

from wemute.domain import MediaKind
from wemute.probe import expand_paths, probe_file


def test_image_probe_reads_dimensions_and_creates_thumbnail(tmp_path: Path) -> None:
    source = tmp_path / "desk-lamp.png"
    Image.new("RGB", (320, 180), (214, 202, 184)).save(source)
    descriptor = probe_file(source)
    assert descriptor.kind == MediaKind.IMAGE
    assert (descriptor.width, descriptor.height) == (320, 180)
    assert descriptor.thumbnail_path
    assert Path(descriptor.thumbnail_path).exists()


def test_expand_paths_is_recursive_and_deduplicated(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    first = tmp_path / "one.png"
    second = nested / "two.png"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    expanded = expand_paths([tmp_path, first])
    assert expanded == [second.resolve(), first.resolve()]
