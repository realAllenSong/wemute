from __future__ import annotations

import hashlib
import io
import os
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from wemute.components import ComponentManager, ComponentManifest, load_component_manifests, platform_tag
from wemute.components_qt import ComponentController, size_label
from wemute.model_packages import ChecksumMismatch

TOOL = "#!/bin/sh\necho tool 1.0\n"


def _manifest(data: bytes, archive_format: str, member: str, executable: str, **extra) -> ComponentManifest:
    return ComponentManifest(
        id=extra.pop("id", "tool"),
        name="Tool",
        version="1.0",
        filename=f"tool.{archive_format}",
        download_url=f"https://example.com/tool.{archive_format}",
        sha256=extra.pop("sha256", hashlib.sha256(data).hexdigest()),
        size_bytes=len(data),
        license="MIT",
        license_url="https://example.com/license",
        archive_format=archive_format,
        members=(member,),
        executable=executable,
        **extra,
    )


def _zip_tool() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("tool-1.0/bin/tool", TOOL)
        bundle.writestr("tool-1.0/README", "not needed")
    return buffer.getvalue()


def _opener(data: bytes):
    return lambda _url: io.BytesIO(data)


def test_zip_component_installs_only_declared_members(tmp_path: Path) -> None:
    data = _zip_tool()
    manifest = _manifest(data, "zip", "tool-1.0/bin/tool", "tool-1.0/bin/tool", warmup=("--version",))
    manager = ComponentManager(tmp_path, [manifest])
    stages: list[str] = []

    executable = manager.install(manifest, progress=lambda stage, *_: stages.append(stage), opener=_opener(data))

    assert executable.is_file() and os.access(executable, os.X_OK)
    assert manager.installed(manifest)
    assert manager.tools() == {"tool": str(executable)}
    assert not (manager.runtime_dir(manifest) / "tool-1.0" / "README").exists()
    assert stages[0] == "download" and stages[-1] == "install"
    assert manager.disk_usage(manifest) > 0
    # The verified archive is deleted once unpacked.
    assert not list((tmp_path / "downloads").rglob("tool.zip*"))

    manager.remove(manifest)
    assert not manager.installed(manifest)
    assert manager.tools() == {}
    assert not (tmp_path / "tool").exists()


def test_checksum_mismatch_installs_nothing(tmp_path: Path) -> None:
    data = _zip_tool()
    manifest = _manifest(data, "zip", "tool-1.0/bin/tool", "tool-1.0/bin/tool", sha256="0" * 64)
    manager = ComponentManager(tmp_path, [manifest])

    with pytest.raises(ChecksumMismatch):
        manager.install(manifest, opener=_opener(data))
    assert not manager.installed(manifest)
    assert not manager.runtime_dir(manifest).exists()


@pytest.mark.skipif(not Path("/usr/bin/hdiutil").exists(), reason="needs hdiutil")
def test_dmg_component_is_copied_out_of_a_read_only_image(tmp_path: Path) -> None:
    app = tmp_path / "image" / "Tool.app" / "Contents" / "MacOS"
    app.mkdir(parents=True)
    (app / "tool").write_text(TOOL)
    (app / "tool").chmod(0o755)
    dmg = tmp_path / "tool.dmg"
    subprocess.run(
        ["/usr/bin/hdiutil", "create", "-quiet", "-fs", "HFS+", "-format", "UDZO",
         "-srcfolder", str(tmp_path / "image"), "-volname", "Tool", str(dmg)],
        check=True,
    )
    data = dmg.read_bytes()
    manifest = _manifest(data, "dmg", "Tool.app", "Tool.app/Contents/MacOS/tool")
    manager = ComponentManager(tmp_path / "components", [manifest])

    executable = manager.install(manifest, opener=_opener(data))

    assert executable.is_file()
    assert subprocess.run([str(executable)], capture_output=True, text=True).stdout == "tool 1.0\n"
    mounted = subprocess.run(["/usr/bin/hdiutil", "info"], capture_output=True, text=True).stdout
    assert "wemute-dmg-" not in mounted


def test_manifests_reject_unsafe_members() -> None:
    with pytest.raises(ValueError):
        _manifest(b"x", "zip", "../escape", "../escape").validate()
    with pytest.raises(ValueError):
        _manifest(b"x", "zip", "tool/bin/tool", "other/bin/tool").validate()


def test_bundled_catalog_is_pinned_and_filtered_by_platform() -> None:
    manifests = load_component_manifests()
    assert all(not item.platforms or platform_tag() in item.platforms for item in manifests)
    for item in manifests:
        assert item.download_url.startswith("https://")
        assert len(item.sha256) == 64 and item.size_bytes > 1_000_000
    if platform_tag() == "macos-arm64":
        assert {item.id for item in manifests} == {"libreoffice", "calibre", "pandoc"}


class _InstantManager(ComponentManager):
    """Installs a stub executable without any download."""

    def __init__(self, root: Path, manifests: list[ComponentManifest], fail: bool = False) -> None:
        super().__init__(root, manifests)
        self.fail = fail

    def install(self, manifest, progress=None, cancel=None, opener=None):  # noqa: ANN001
        if progress:
            progress("download", manifest.size_bytes, manifest.size_bytes)
        if self.fail:
            raise OSError("network is down")
        runtime = self.runtime_dir(manifest)
        executable = runtime / manifest.executable
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(TOOL)
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        (runtime / ".wemute-component.json").write_text(
            f'{{"sha256": "{manifest.sha256}", "disk_bytes": 10}}'
        )
        return executable


def _wait(condition, timeout_ms: int = 5000) -> bool:
    loop = QEventLoop()
    poll = QTimer()
    poll.timeout.connect(lambda: condition() and loop.quit())
    poll.start(20)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    poll.stop()
    return condition()


def test_controller_installs_queued_components_one_at_a_time(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    first = _manifest(b"a" * 10, "zip", "a/bin/a", "a/bin/a", id="first")
    second = _manifest(b"b" * 10, "zip", "b/bin/b", "b/bin/b", id="second")
    controller = ComponentController(_InstantManager(tmp_path, [first, second]))
    ready: list[str] = []
    controller.componentReady.connect(ready.append)

    controller.install("first")
    controller.install("second")
    assert controller.status("second")["queued"]

    assert _wait(lambda: ready == ["first", "second"])
    assert controller.is_installed("first") and controller.is_installed("second")
    assert set(controller.tools()) == {"first", "second"}

    controller.remove("first")
    assert not controller.is_installed("first")
    controller.shutdown()


def test_controller_reports_a_failed_install(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    manifest = _manifest(b"a" * 10, "zip", "a/bin/a", "a/bin/a")
    controller = ComponentController(_InstantManager(tmp_path, [manifest], fail=True))
    failures: list[tuple[str, str]] = []
    controller.installFailed.connect(lambda component, error: failures.append((component, error)))

    controller.install("tool")

    assert _wait(lambda: bool(failures))
    assert failures == [("tool", "network is down")]
    assert controller.status("tool")["error"] == "network is down"
    controller.shutdown()


def test_size_labels_use_decimal_units() -> None:
    assert size_label(298_845_477) == "299 MB"
    assert size_label(1_179_913_856) == "1.2 GB"
    assert size_label(42_313_957) == "42 MB"
