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
        "name": "FFmpeg",
        "version": "8.1.2",
        "license": "LGPL-2.1-or-later",
        "url": "https://ffmpeg.org/legal.html",
    },
    {
        "name": "LAME",
        "version": "3.100",
        "license": "LGPL-2.0-or-later",
        "url": "https://sourceforge.net/projects/lame/files/lame/",
    },
    {
        "name": "Opus",
        "version": "1.6.1",
        "license": "BSD-3-Clause",
        "url": "https://github.com/xiph/opus/blob/main/COPYING",
    },
    {
        "name": "libvpx",
        "version": "1.16.0",
        "license": "BSD-3-Clause",
        "url": "https://chromium.googlesource.com/webm/libvpx/+/refs/heads/main/LICENSE",
    },
    {
        "name": "Sparkle",
        "version": "2.9.2",
        "license": "MIT",
        "url": "https://github.com/sparkle-project/Sparkle/blob/2.x/LICENSE",
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
    {
        "name": "BiRefNet optional model",
        "version": "general-lite-232",
        "license": "MIT",
        "url": "https://github.com/ZhengPeng7/BiRefNet/blob/main/LICENSE",
    },
    {
        "name": "Real-ESRGAN / ncnn optional runtime",
        "version": "0.2.5.0",
        "license": "BSD-3-Clause",
        "url": "https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE",
    },
    {
        "name": "OpenCV LaMa optional model",
        "version": "2025jan",
        "license": "Apache-2.0",
        "url": "https://huggingface.co/opencv/inpainting_lama/blob/main/LICENSE",
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
