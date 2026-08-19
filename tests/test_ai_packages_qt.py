from pathlib import Path

from PySide6.QtCore import QCoreApplication

from wemute.ai_packages_qt import AIModelController
from wemute.model_packages import ModelManifest, ModelPackageManager


def test_catalog_exposes_download_consent_details(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    manifest = ModelManifest(
        id="u2net",
        name="Background Removal · Fast",
        version="1",
        capability="remove-background",
        filename="u2netp.onnx",
        download_url="https://example.com/u2netp.onnx",
        sha256="0" * 64,
        size_bytes=4_574_861,
        license="Apache-2.0",
        license_url="https://example.com/license",
        backend="onnxruntime-u2net",
        description="Runs locally.",
    )
    controller = AIModelController(
        ModelPackageManager(tmp_path, [manifest]),
        lambda _actions: None,
    )

    row = controller.catalog[0]
    assert row["name"] == manifest.name
    assert row["sizeLabel"] == "4.4 MB"
    assert row["license"] == "Apache-2.0"
    assert row["installed"] is False
    controller.shutdown()
