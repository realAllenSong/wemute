from __future__ import annotations

from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtGui import QDesktopServices

from wemute import __version__


THIRD_PARTY_COMPONENTS: tuple[dict[str, str], ...] = (
    {
        "name": "Qt for Python / PySide6",
        "version": "6.10.3",
        "license": "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only",
        "url": "https://www.qt.io/licensing/open-source-lgpl-obligations",
    },
    {
        "name": "NumPy",
        "version": "2.5.2",
        "license": "BSD-3-Clause and bundled third-party licenses",
        "url": "https://numpy.org/doc/stable/license.html",
    },
    {
        "name": "Pillow",
        "version": "12.3.0",
        "license": "MIT-CMU",
        "url": "https://github.com/python-pillow/Pillow/blob/main/LICENSE",
    },
    {
        "name": "pillow-heif",
        "version": "1.5.0",
        "license": "BSD-3-Clause",
        "url": "https://github.com/bigcat88/pillow_heif/blob/master/LICENSE.txt",
    },
    {
        "name": "libheif / libde265",
        "version": "1.23.1 / 1.1.1",
        "license": "LGPL-3.0 (bundled by pillow-heif)",
        "url": "https://github.com/strukturag/libheif/blob/master/COPYING",
    },
    {
        "name": "x265 HEVC encoder",
        "version": "4.2",
        "license": "GPL-2.0-or-later or commercial (Alpha build only)",
        "url": "https://github.com/videolan/x265/blob/master/COPYING",
    },
    {
        "name": "ONNX Runtime",
        "version": "1.29.0",
        "license": "MIT",
        "url": "https://github.com/microsoft/onnxruntime/blob/main/LICENSE",
    },
    {
        "name": "platformdirs",
        "version": "4.11.3",
        "license": "MIT",
        "url": "https://github.com/tox-dev/platformdirs/blob/main/LICENSE",
    },
    {
        "name": "PyInstaller bootloader",
        "version": "6.22.2",
        "license": "GPL-2.0-or-later with bootloader distribution exception",
        "url": "https://pyinstaller.org/en/stable/license.html",
    },
    {
        "name": "U²-NetP optional model",
        "version": "2020.1",
        "license": "Apache-2.0",
        "url": "https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE",
    },
)


class AppInfoController(QObject):
    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property("QVariantList", constant=True)
    def thirdParty(self) -> list[dict[str, str]]:
        return [dict(component) for component in THIRD_PARTY_COMPONENTS]

    @Slot(str)
    def openUrl(self, url: str) -> None:
        parsed = QUrl(url)
        if parsed.scheme() == "https":
            QDesktopServices.openUrl(parsed)
