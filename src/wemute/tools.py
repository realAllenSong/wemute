"""Apple Vision and Core Image tools offered as choices in the sentence menus.

A tool is a choice like a format: it is stored in ``JobRecord.target_format``
under its key and runs in the document worker (``wemute.convert_worker``) so
Vision never blocks the UI. Tools sharing a ``family`` are drawn as one menu
row with small variant chips ("智能裁剪  1:1 4:5 16:9 9:16").
"""

from __future__ import annotations

import importlib.util
import platform
import sys
from dataclasses import dataclass
from functools import lru_cache

from wemute.domain import MediaKind

RECOGNIZE = "recognize"
PHOTO = "photo"
_IMAGE = frozenset({MediaKind.IMAGE})
_IMAGE_PDF = frozenset({MediaKind.IMAGE, MediaKind.PDF})


@dataclass(frozen=True, slots=True)
class Tool:
    key: str
    kinds: frozenset[MediaKind]
    section: str
    engine: str
    # Output extension; empty keeps the photo's own format.
    extension: str = ""
    # One output from the whole group, like "合成一个 PDF".
    group: bool = False
    folder: bool = False
    options: tuple[tuple[str, object], ...] = ()
    family: str = ""
    min_files: int = 1
    icon: str = ""


TOOLS: tuple[Tool, ...] = (
    Tool("Text (OCR)", _IMAGE_PDF, RECOGNIZE, "ocr", ".txt", options=(("format", "txt"),), family="ocr", icon="scan-text"),
    Tool("Word (OCR)", _IMAGE, RECOGNIZE, "ocr", ".docx", options=(("format", "docx"),), family="ocr", icon="scan-text"),
    Tool("Searchable PDF", _IMAGE_PDF, RECOGNIZE, "ocr", ".pdf", options=(("format", "pdf"),), family="ocr", icon="scan-text"),
    Tool("Scan to PDF", _IMAGE, RECOGNIZE, "scan", ".pdf", options=(("mode", "color"),), family="scan_pdf", icon="scan"),
    Tool("Scan to PDF B&W", _IMAGE, RECOGNIZE, "scan", ".pdf", options=(("mode", "bw"),), family="scan_pdf", icon="scan"),
    Tool("Scan to JPG", _IMAGE, RECOGNIZE, "scan", ".jpg", options=(("mode", "color"),), family="scan_jpg", icon="scan"),
    Tool("Scan to JPG B&W", _IMAGE, RECOGNIZE, "scan", ".jpg", options=(("mode", "bw"),), family="scan_jpg", icon="scan"),
    Tool("Read codes", _IMAGE, RECOGNIZE, "codes", ".txt", icon="qr-code"),
    Tool("One searchable PDF", _IMAGE, RECOGNIZE, "ocr", ".pdf", True, options=(("format", "pdf"),), min_files=2, icon="layers"),
    Tool("One scanned PDF", _IMAGE, RECOGNIZE, "scan", ".pdf", True, options=(("mode", "color"),), family="scan_one", min_files=2, icon="layers"),
    Tool("One scanned PDF B&W", _IMAGE, RECOGNIZE, "scan", ".pdf", True, options=(("mode", "bw"),), family="scan_one", min_files=2, icon="layers"),
    Tool("Codes CSV", _IMAGE, RECOGNIZE, "codes", ".csv", True, min_files=2, icon="qr-code"),
    Tool("Blurry & duplicates", _IMAGE, RECOGNIZE, "triage", "", True, True, min_files=2, icon="images"),
    Tool("Smart crop 1:1", _IMAGE, PHOTO, "crop", options=(("ratio", "1:1"),), family="crop", icon="crop"),
    Tool("Smart crop 4:5", _IMAGE, PHOTO, "crop", options=(("ratio", "4:5"),), family="crop", icon="crop"),
    Tool("Smart crop 16:9", _IMAGE, PHOTO, "crop", options=(("ratio", "16:9"),), family="crop", icon="crop"),
    Tool("Smart crop 9:16", _IMAGE, PHOTO, "crop", options=(("ratio", "9:16"),), family="crop", icon="crop"),
    Tool("Blur faces", _IMAGE, PHOTO, "faces", options=(("style", "blur"),), family="faces", icon="face"),
    Tool("Pixelate faces", _IMAGE, PHOTO, "faces", options=(("style", "pixelate"),), family="faces", icon="face"),
    Tool("ID photo white", _IMAGE, PHOTO, "id_photo", options=(("color", "white"),), family="id_photo", icon="id-card"),
    Tool("ID photo blue", _IMAGE, PHOTO, "id_photo", options=(("color", "blue"),), family="id_photo", icon="id-card"),
    Tool("ID photo red", _IMAGE, PHOTO, "id_photo", options=(("color", "red"),), family="id_photo", icon="id-card"),
    Tool("Straighten", _IMAGE, PHOTO, "straighten", icon="level"),
    Tool("Auto enhance", _IMAGE, PHOTO, "enhance", icon="wand"),
)

TOOL_BY_KEY = {tool.key: tool for tool in TOOLS}


@lru_cache(maxsize=1)
def vision_available() -> bool:
    """Every tool needs Apple Vision and Core Image from macOS 14 or later."""
    if sys.platform != "darwin":
        return False
    try:
        major = int(platform.mac_ver()[0].split(".")[0])
    except ValueError:
        return False
    return (
        major >= 14
        and importlib.util.find_spec("Vision") is not None
        and importlib.util.find_spec("Quartz") is not None
    )


def tool_for(key: str) -> Tool | None:
    tool = TOOL_BY_KEY.get(key)
    return tool if tool and vision_available() else None


def is_tool(key: str) -> bool:
    return key in TOOL_BY_KEY


def is_group_tool(key: str) -> bool:
    tool = TOOL_BY_KEY.get(key)
    return bool(tool and tool.group)


def tools_for(kind: MediaKind, count: int = 1) -> list[Tool]:
    """Tools offered for a group of ``count`` files of ``kind``, menu order."""
    if not vision_available():
        return []
    return [
        tool
        for tool in TOOLS
        if kind in tool.kinds and (not tool.group or count >= tool.min_files)
    ]


# ── wording ──────────────────────────────────────────────────────────────

SECTION_TITLES = {
    "zh": {"formats": "格式", RECOGNIZE: "识别与整理", PHOTO: "照片工具", "ai": "AI"},
    "en": {"formats": "Formats", RECOGNIZE: "Recognize & organize", PHOTO: "Photo tools", "ai": "AI"},
}

# key: (menu label, pill label). Variants show only their chip in the menu.
_TEXT = {
    "zh": {
        "Text (OCR)": ("TXT", "文字"),
        "Word (OCR)": ("Word", "Word 文档"),
        "Searchable PDF": ("可搜索 PDF", "可搜索的 PDF"),
        "Scan to PDF": ("彩色", "PDF · 彩色"),
        "Scan to PDF B&W": ("黑白", "PDF · 黑白"),
        "Scan to JPG": ("彩色", "JPG · 彩色"),
        "Scan to JPG B&W": ("黑白", "JPG · 黑白"),
        "Read codes": ("识别二维码和条码", "二维码和条码"),
        "One searchable PDF": ("识别成一个可搜索的 PDF", "一个可搜索的 PDF"),
        "One scanned PDF": ("彩色", "一个 PDF · 彩色"),
        "One scanned PDF B&W": ("黑白", "一个 PDF · 黑白"),
        "Codes CSV": ("二维码和条码汇总成一个 CSV", "二维码和条码 · CSV"),
        "Blurry & duplicates": ("挑出模糊和重复的照片", "挑出模糊和重复"),
        "Smart crop 1:1": ("1:1", "智能裁剪 1:1"),
        "Smart crop 4:5": ("4:5", "智能裁剪 4:5"),
        "Smart crop 16:9": ("16:9", "智能裁剪 16:9"),
        "Smart crop 9:16": ("9:16", "智能裁剪 9:16"),
        "Blur faces": ("模糊", "人脸打码"),
        "Pixelate faces": ("马赛克", "人脸马赛克"),
        "ID photo white": ("白", "证件照换白底"),
        "ID photo blue": ("蓝", "证件照换蓝底"),
        "ID photo red": ("红", "证件照换红底"),
        "Straighten": ("自动扶正", "自动扶正"),
        "Auto enhance": ("一键增强", "一键增强"),
    },
    "en": {
        "Text (OCR)": ("TXT", "text"),
        "Word (OCR)": ("Word", "a Word document"),
        "Searchable PDF": ("PDF", "a searchable PDF"),
        "Scan to PDF": ("Color", "PDF · color"),
        "Scan to PDF B&W": ("B&W", "PDF · B&W"),
        "Scan to JPG": ("Color", "JPG · color"),
        "Scan to JPG B&W": ("B&W", "JPG · B&W"),
        "Read codes": ("Read QR codes & barcodes", "text"),
        "One searchable PDF": ("One searchable PDF", "one searchable PDF"),
        "One scanned PDF": ("Color", "one PDF · color"),
        "One scanned PDF B&W": ("B&W", "one PDF · B&W"),
        "Codes CSV": ("All codes into one CSV", "one CSV"),
        "Blurry & duplicates": ("Find blurry & duplicate photos", "blurry & duplicates"),
        "Smart crop 1:1": ("1:1", "smart crop 1:1"),
        "Smart crop 4:5": ("4:5", "smart crop 4:5"),
        "Smart crop 16:9": ("16:9", "smart crop 16:9"),
        "Smart crop 9:16": ("9:16", "smart crop 9:16"),
        "Blur faces": ("Blur", "blurred faces"),
        "Pixelate faces": ("Pixelate", "pixelated faces"),
        "ID photo white": ("White", "ID photo · white"),
        "ID photo blue": ("Blue", "ID photo · blue"),
        "ID photo red": ("Red", "ID photo · red"),
        "Straighten": ("Straighten", "straightening"),
        "Auto enhance": ("Auto enhance", "auto enhance"),
    },
}

FAMILY_TITLES = {
    "zh": {
        "ocr": "识别文字",
        "scan_pdf": "扫描成 PDF",
        "scan_jpg": "扫描成 JPG",
        "scan_one": "扫描成一个 PDF",
        "crop": "智能裁剪",
        "faces": "人脸打码",
        "id_photo": "证件照换底",
    },
    "en": {
        "ocr": "Recognize text",
        "scan_pdf": "Scan to PDF",
        "scan_jpg": "Scan to JPG",
        "scan_one": "Scan into one PDF",
        "crop": "Smart crop",
        "faces": "Hide faces",
        "id_photo": "ID photo",
    },
}

# Lead and verb around the count, by engine: "把 3 张图片 识别成 [文字]".
_WORDS = {
    "zh": {
        "ocr": ("把", "识别成"),
        "scan": ("把", "扫描成"),
        "codes": ("识别", "里的"),
        "triage": ("从", "里"),
        PHOTO: ("给", ""),
    },
    "en": {
        "ocr": ("Turn", "into"),
        "scan": ("Scan", "into"),
        "codes": ("Read the codes in", "as"),
        "triage": ("Check", "for"),
        PHOTO: ("Edit", "with"),
    },
}

# Appended to the source name: "海边 打码.jpg"; outputs of another type keep the name.
_NAME_SUFFIX = {
    "zh": {
        "scan": " 扫描",
        "codes": " 二维码",
        "crop": " 裁剪",
        "faces": " 打码",
        "id_photo": " 证件照",
        "straighten": " 扶正",
        "enhance": " 增强",
        "searchable": " 可搜索",
    },
    "en": {
        "scan": " scan",
        "codes": " codes",
        "crop": " crop",
        "faces": " faces hidden",
        "id_photo": " ID photo",
        "straighten": " straightened",
        "enhance": " enhanced",
        "searchable": " searchable",
    },
}

TRIAGE_FOLDER = {"zh": "整理结果", "en": "Photo review"}


def _language(language: str) -> str:
    return language if language in _TEXT else "en"


def menu_label(key: str, language: str = "en") -> str:
    return _TEXT[_language(language)].get(key, (key, key))[0]


def pill_label(key: str, language: str = "en") -> str | None:
    entry = _TEXT[_language(language)].get(key)
    return entry[1] if entry else None


def family_title(family: str, language: str = "en") -> str:
    return FAMILY_TITLES[_language(language)].get(family, family)


def section_title(section: str, language: str = "en") -> str:
    return SECTION_TITLES[_language(language)].get(section, section)


def sentence_words(key: str, language: str = "en") -> tuple[str, str] | None:
    tool = TOOL_BY_KEY.get(key)
    if not tool:
        return None
    words = _WORDS[_language(language)]
    return words.get(tool.engine) or words[PHOTO]


def name_suffix(tool: Tool, language: str, source_kind: MediaKind) -> str:
    suffixes = _NAME_SUFFIX[_language(language)]
    if tool.engine == "ocr":
        return suffixes["searchable"] if source_kind == MediaKind.PDF and tool.extension == ".pdf" else ""
    return suffixes.get(tool.engine, "")
