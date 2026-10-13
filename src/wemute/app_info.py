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
        "name": "Lucide icons",
        "version": "shapes",
        "license": "ISC",
        "url": "https://github.com/lucide-icons/lucide/blob/main/LICENSE",
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
    {
        "name": "demucs-mlx",
        "version": "1.4.6",
        "license": "MIT",
        "url": "https://github.com/ssmall256/demucs-mlx/blob/main/LICENSE",
    },
    {
        "name": "Apple MLX",
        "version": "0.31.2",
        "license": "MIT",
        "url": "https://github.com/ml-explore/mlx/blob/main/LICENSE",
    },
    {
        "name": "mlx-audio-io / mlx-spectro",
        "version": "1.3.11 / 0.7.0",
        "license": "MIT with bundled third-party notices",
        "url": "https://github.com/ssmall256/mlx-audio-io/blob/main/LICENSE",
    },
    {
        "name": "HTDemucs optional model",
        "version": "955717e8",
        "license": "MIT",
        "url": "https://github.com/facebookresearch/demucs/blob/main/LICENSE",
    },
    {
        "name": "PyMuPDF (MuPDF)",
        "version": "1.28.2",
        "license": "AGPL-3.0-only",
        "url": "https://github.com/pymupdf/PyMuPDF/blob/main/COPYING",
    },
    {
        "name": "pdf2docx",
        "version": "0.5.13",
        "license": "MIT",
        "url": "https://github.com/ArtifexSoftware/pdf2docx/blob/master/LICENSE",
    },
    {
        "name": "pypdfium2 / PDFium",
        "version": "5.14.0",
        "license": "Apache-2.0 OR BSD-3-Clause; PDFium BSD-3-Clause",
        "url": "https://github.com/pypdfium2-team/pypdfium2/tree/main/LICENSES",
    },
    {
        "name": "pikepdf / qpdf",
        "version": "10.17.0",
        "license": "MPL-2.0; qpdf Apache-2.0",
        "url": "https://github.com/pikepdf/pikepdf/blob/main/LICENSE.txt",
    },
    {
        "name": "OpenCV (headless)",
        "version": "5.0.0.93",
        "license": "Apache-2.0",
        "url": "https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt",
    },
    {
        "name": "openpyxl / et-xmlfile",
        "version": "3.1.5 / 2.0.0",
        "license": "MIT",
        "url": "https://foss.heptapod.net/openpyxl/openpyxl/-/blob/branch/default/LICENCE.rst",
    },
    {
        "name": "python-docx / lxml",
        "version": "1.2.0 / 6.1.3",
        "license": "MIT / BSD-3-Clause",
        "url": "https://github.com/python-openxml/python-docx/blob/master/LICENSE",
    },
    {
        "name": "fontTools / Brotli",
        "version": "4.66.1 / 1.2.0",
        "license": "MIT",
        "url": "https://github.com/fonttools/fonttools/blob/main/LICENSE",
    },
    {
        "name": "py7zr (pyppmd, pybcj, inflate64, multivolumefile)",
        "version": "1.1.4",
        "license": "LGPL-2.1-or-later",
        "url": "https://github.com/miurahr/py7zr/blob/master/LICENSE",
    },
    {
        "name": "Python-Markdown",
        "version": "3.11",
        "license": "BSD-3-Clause",
        "url": "https://github.com/Python-Markdown/markdown/blob/master/LICENSE.md",
    },
    {
        "name": "LibreOffice optional component",
        "version": "26.8.1",
        "license": "MPL-2.0",
        "url": "https://www.libreoffice.org/about-us/licenses/",
    },
    {
        "name": "Calibre optional component",
        "version": "9.16.0",
        "license": "GPL-3.0-only",
        "url": "https://github.com/kovidgoyal/calibre/blob/master/LICENSE",
    },
    {
        "name": "Pandoc optional component",
        "version": "3.12.1",
        "license": "GPL-2.0-or-later",
        "url": "https://github.com/jgm/pandoc/blob/main/COPYRIGHT",
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
