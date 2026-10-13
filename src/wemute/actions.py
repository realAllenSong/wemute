"""Every action the app offers, for the 工具 menu, the menu bar and ⌘K.

An action either applies a choice to the files of some kinds ("去背景" puts
``Remove Background`` on the images) or runs an app command ("添加文件…").
The registry is plain data so menus and search can be tested without Qt.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from wemute.capabilities import (
    COMBINE_PDF,
    EXTRACT,
    MERGE_PDF,
    PACK_ZIP,
    PER_PAGE_JPG,
    PER_PAGE_PNG,
    SMALLER_PDF,
    SOURCE_SUFFIXES,
    options_for,
)
from wemute.domain import MediaKind, OperationKind
from wemute.presentation import GROUP_LABELS, choice_label

Text = tuple[str, str]  # (zh, en)

VISION = "vision"
UPDATER = "updater"
THUNDERTALK = "thundertalk"

SECTIONS: dict[str, Text] = {
    "convert": ("转换", "Convert"),
    "image": ("图片工具", "Image tools"),
    "av": ("音视频", "Audio & video"),
    "more": ("更多", "More"),
    "app": ("Wemute", "Wemute"),
}
TOOL_SECTIONS = ("convert", "image", "av", "more")

# Submenus inside a section; "formats/<kind>" nests under "formats".
GROUPS: dict[str, tuple[Text, str]] = {
    "pdf": (("PDF", "PDF"), "file-text"),
    "formats": (("按格式转换", "Convert to format"), "convert"),
    "ocr": (("文字识别（OCR）", "Recognize text (OCR)"), "scan-text"),
    "scan": (("扫描矫正", "Scan & flatten"), "scan"),
    "faces": (("人脸打码", "Hide faces"), "face"),
    "id_photo": (("证件照换底", "ID photo background"), "id-card"),
    "crop": (("智能裁剪", "Smart crop"), "crop"),
    "photo_more": (("更多照片工具", "More photo tools"), "wand"),
    "subtitles": (("生成字幕", "Subtitles"), "captions"),
}

KIND_NOUNS: dict[MediaKind, Text] = {
    MediaKind.IMAGE: ("图片", "images"),
    MediaKind.VIDEO: ("视频", "videos"),
    MediaKind.AUDIO: ("音频", "audio"),
    MediaKind.DOCUMENT: ("文档", "documents"),
    MediaKind.SPREADSHEET: ("表格", "spreadsheets"),
    MediaKind.PRESENTATION: ("演示文稿", "presentations"),
    MediaKind.PDF: ("PDF", "PDFs"),
    MediaKind.EBOOK: ("电子书", "ebooks"),
    MediaKind.ARCHIVE: ("压缩包", "archives"),
    MediaKind.DATA: ("文本文件", "text files"),
    MediaKind.FONT: ("字体", "fonts"),
    MediaKind.VECTOR: ("SVG 图形", "SVG graphics"),
}
# What to drop, in hints: "拖入照片就会…".
DROP_NOUNS: dict[MediaKind, Text] = {**KIND_NOUNS, MediaKind.IMAGE: ("照片或图片", "photos or images")}

FORMAT_KINDS = (
    MediaKind.IMAGE,
    MediaKind.VIDEO,
    MediaKind.AUDIO,
    MediaKind.DOCUMENT,
    MediaKind.SPREADSHEET,
    MediaKind.PRESENTATION,
    MediaKind.PDF,
    MediaKind.EBOOK,
    MediaKind.DATA,
    MediaKind.FONT,
    MediaKind.VECTOR,
)
ALL_KINDS = (*FORMAT_KINDS, MediaKind.ARCHIVE)

_MEDIA_SUFFIXES = {
    MediaKind.IMAGE: ("heic", "heif", "jpg", "jpeg", "png", "webp", "gif", "tiff", "bmp", "avif", "raw", "dng"),
    MediaKind.VIDEO: ("mov", "mp4", "m4v", "mkv", "avi", "webm"),
    MediaKind.AUDIO: ("wav", "mp3", "m4a", "aac", "flac", "aiff", "ogg", "opus"),
}
_KIND_WORDS = {
    MediaKind.IMAGE: ("照片", "相片", "photo", "picture", "image"),
    MediaKind.VIDEO: ("影片", "movie", "video"),
    MediaKind.AUDIO: ("声音", "音乐", "sound", "music", "audio"),
    MediaKind.DOCUMENT: ("word", "pages", "文稿", "document", "doc"),
    MediaKind.SPREADSHEET: ("excel", "numbers", "spreadsheet", "sheet"),
    MediaKind.PRESENTATION: ("ppt", "powerpoint", "keynote", "幻灯片", "slides"),
    MediaKind.PDF: ("pdf",),
    MediaKind.EBOOK: ("kindle", "ebook", "book"),
    MediaKind.ARCHIVE: ("zip", "rar", "7z", "archive", "解压"),
    MediaKind.DATA: ("markdown", "json", "html", "text", "文本"),
    MediaKind.FONT: ("font", "ttf", "otf", "woff"),
    MediaKind.VECTOR: ("svg", "vector", "矢量"),
}


def kind_keywords(kind: MediaKind) -> tuple[str, ...]:
    suffixes = _MEDIA_SUFFIXES.get(kind) or tuple(
        sorted(suffix.lstrip(".") for suffix in SOURCE_SUFFIXES.get(kind, ()))
    )
    return (*suffixes, *_KIND_WORDS.get(kind, ()), *KIND_NOUNS[kind], GROUP_LABELS["zh"][kind], GROUP_LABELS["en"][kind])


@dataclass(frozen=True, slots=True)
class Action:
    id: str
    section: str
    title: Text
    icon: str
    tint: str = "neutral"
    # Longer wording for ⌘K; the menu title by default.
    palette_title: Text | None = None
    category: Text | None = None
    choices: tuple[tuple[MediaKind, str], ...] = ()
    # What to drop when no matching files are open: "拖入照片就会抠出主体".
    hint: Text = ("", "")
    keywords: tuple[str, ...] = ()
    # Output formats the action produces, so "转 pdf" ranks PDF outputs first.
    targets: tuple[str, ...] = ()
    requires: OperationKind | str | None = None
    command: str = ""
    group: str = ""
    shortcut: str = ""
    in_tools: bool = True
    in_palette: bool = True


def text(value: Text, language: str) -> str:
    return value[0] if language == "zh" else value[1]


_CJK = r"\u3400-\u9fff\uf900-\ufaff"


def _spaced(value: str) -> str:
    """Chinese next to Latin letters gets a space: "把PDF转成" → "把 PDF 转成"."""
    value = re.sub(rf"([{_CJK}])([A-Za-z0-9])", r"\1 \2", value)
    return re.sub(rf"([A-Za-z0-9)])([{_CJK}])", r"\1 \2", value)


def _ai(kind: MediaKind, label: str) -> tuple[tuple[MediaKind, str], ...]:
    return ((kind, label),)


def _tool(key: str) -> tuple[tuple[MediaKind, str], ...]:
    from wemute.tools import TOOL_BY_KEY

    tool = TOOL_BY_KEY[key]
    order = {kind: index for index, kind in enumerate(ALL_KINDS)}
    return tuple((kind, key) for kind in sorted(tool.kinds, key=order.__getitem__))


_CONVERT = ("转换", "转", "convert")

_NAMED: tuple[Action, ...] = (
    # ── 转换 ──────────────────────────────────────────────────────────────
    Action(
        "to_pdf", "convert", ("转成 PDF…", "Convert to PDF…"), "file-text", "pdf",
        choices=tuple((kind, "PDF") for kind in (
            MediaKind.DOCUMENT, MediaKind.SPREADSHEET, MediaKind.PRESENTATION,
            MediaKind.EBOOK, MediaKind.DATA, MediaKind.VECTOR,
        )),
        hint=("拖入文档、表格、演示文稿或电子书就会转成 PDF",
              "Drop documents, spreadsheets, slides or ebooks to turn them into PDFs"),
        keywords=_CONVERT, targets=("pdf",), in_palette=False,
    ),
    Action(
        "images_to_pdf", "convert", ("合成一个 PDF", "Combine into one PDF"), "layers", "image",
        palette_title=("把图片合成一个 PDF", "Combine images into one PDF"),
        category=("图片", "Images"),
        choices=((MediaKind.IMAGE, COMBINE_PDF),),
        hint=("拖入几张图片就会按顺序合成一个 PDF", "Drop a few images to combine them into one PDF, in order"),
        keywords=(*_CONVERT, "合并", "merge", "图片转pdf", "photos"), targets=("pdf",),
    ),
    Action(
        "pack_zip", "convert", ("打包成 ZIP", "Pack into a ZIP"), "package", "archive",
        palette_title=("把文件打包成一个 ZIP", "Pack files into one ZIP"),
        category=("压缩包", "Archives"),
        choices=tuple((kind, PACK_ZIP) for kind in ALL_KINDS),
        hint=("拖入任意文件就会打包成一个 ZIP", "Drop any files to pack them into one ZIP"),
        keywords=("压缩", "打包", "compress", "zip", "archive"), targets=("zip",),
    ),
    Action(
        "extract", "convert", ("解压压缩包", "Extract archives"), "folder-open", "archive",
        category=("压缩包", "Archives"),
        choices=((MediaKind.ARCHIVE, EXTRACT),),
        hint=("拖入 ZIP、7Z 或 RAR 就会解压成文件夹", "Drop ZIP, 7Z or RAR files to extract them into folders"),
        keywords=("解压", "unzip", "extract", "zip", "rar", "7z", "unpack"),
    ),
    Action(
        "pdf_to_word", "convert", ("PDF 转 Word", "PDF to Word"), "file-text", "pdf", group="pdf",
        category=("PDF", "PDF"), choices=((MediaKind.PDF, "DOCX"),),
        hint=("拖入 PDF 就会转成可编辑的 Word 文档", "Drop PDFs to turn them into editable Word documents"),
        keywords=(*_CONVERT, "docx", "word", "编辑"), targets=("docx", "word"),
    ),
    Action(
        "merge_pdf", "convert", ("合并多个 PDF", "Merge PDFs"), "layers", "pdf", group="pdf",
        category=("PDF", "PDF"), choices=((MediaKind.PDF, MERGE_PDF),),
        hint=("拖入几个 PDF 就会按顺序合并成一个", "Drop a few PDFs to merge them into one, in order"),
        keywords=(*_CONVERT, "合并", "合成", "merge", "combine", "join"), targets=("pdf",),
    ),
    Action(
        "compress_pdf", "convert", ("压缩 PDF", "Make PDFs smaller"), "file-text", "pdf", group="pdf",
        category=("PDF", "PDF"), choices=((MediaKind.PDF, SMALLER_PDF),),
        hint=("拖入 PDF 就会压缩成更小的文件", "Drop PDFs to make them smaller"),
        keywords=("压缩", "变小", "减小", "compress", "smaller", "shrink", "reduce"), targets=("pdf",),
    ),
    Action(
        "pdf_to_png", "convert", ("每页转成 PNG", "Each page to PNG"), "image", "pdf", group="pdf",
        palette_title=("把 PDF 每页转成 PNG 图片", "Turn each PDF page into a PNG"),
        category=("PDF", "PDF"), choices=((MediaKind.PDF, PER_PAGE_PNG),),
        hint=("拖入 PDF 就会把每一页存成 PNG", "Drop PDFs to save every page as a PNG"),
        keywords=(*_CONVERT, "图片", "image", "pages"), targets=("png",),
    ),
    Action(
        "pdf_to_jpg", "convert", ("每页转成 JPG", "Each page to JPG"), "image", "pdf", group="pdf",
        palette_title=("把 PDF 每页转成 JPG 图片", "Turn each PDF page into a JPG"),
        category=("PDF", "PDF"), choices=((MediaKind.PDF, PER_PAGE_JPG),),
        hint=("拖入 PDF 就会把每一页存成 JPG", "Drop PDFs to save every page as a JPG"),
        keywords=(*_CONVERT, "图片", "image", "jpeg", "pages"), targets=("jpg", "jpeg"),
    ),
    # ── 图片工具 ──────────────────────────────────────────────────────────
    Action(
        "remove_background", "image", ("去背景", "Remove background"), "scissors", "image",
        category=("图片 · AI", "Images · AI"),
        choices=_ai(MediaKind.IMAGE, "Remove Background"),
        hint=("拖入照片就会抠出主体", "drop a photo and its subject is cut out"),
        keywords=("抠图", "去底", "背景", "透明", "cutout", "cut out", "background", "transparent", "png", "ai"),
        requires=OperationKind.REMOVE_BACKGROUND,
    ),
    Action(
        "erase", "image", ("擦除…", "Erase…"), "eraser", "image",
        palette_title=("擦除照片里不想要的东西", "Erase unwanted things from a photo"),
        category=("图片 · AI", "Images · AI"),
        choices=_ai(MediaKind.IMAGE, "Erase Object"),
        hint=("拖入照片，涂抹掉不想要的东西", "drop a photo, then paint over what to remove"),
        keywords=("擦除", "去除", "消除", "去水印", "水印", "erase", "remove object", "inpaint", "watermark", "ai"),
        requires=OperationKind.ERASE_OBJECT,
    ),
    Action(
        "ocr_text", "image", ("识别成文字", "Text (TXT)"), "scan-text", "data", group="ocr",
        palette_title=("截图、扫描件转文字（OCR）", "Screenshots and scans to text (OCR)"),
        category=("文字识别", "Recognize text"), choices=_tool("Text (OCR)"),
        hint=("拖入截图、照片或扫描的 PDF 就会识别出文字", "drop screenshots, photos or scanned PDFs to get their text"),
        keywords=("ocr", "文字", "识别", "提取", "截图", "text", "recognize", "txt", "scan"), targets=("txt",),
        requires=VISION,
    ),
    Action(
        "ocr_word", "image", ("识别成 Word 文档", "Word document"), "scan-text", "document", group="ocr",
        palette_title=("图片识别成 Word 文档（OCR）", "Images to a Word document (OCR)"),
        category=("文字识别", "Recognize text"), choices=_tool("Word (OCR)"),
        hint=("拖入截图或照片就会识别成 Word 文档", "drop screenshots or photos to get a Word document"),
        keywords=("ocr", "文字", "识别", "word", "docx", "recognize"), targets=("docx", "word"),
        requires=VISION,
    ),
    Action(
        "ocr_pdf", "image", ("识别成可搜索 PDF", "Searchable PDF"), "scan-text", "pdf", group="ocr",
        palette_title=("扫描件转可搜索 PDF", "Scans to a searchable PDF"),
        category=("文字识别", "Recognize text"), choices=_tool("Searchable PDF"),
        hint=("拖入扫描件或照片就会变成能搜索文字的 PDF", "drop scans or photos to get PDFs you can search"),
        keywords=("ocr", "文字", "识别", "搜索", "searchable", "recognize", "scan", *_CONVERT), targets=("pdf",),
        requires=VISION,
    ),
    Action(
        "ocr_one_pdf", "image", ("合成一个可搜索 PDF", "One searchable PDF"), "layers", "pdf", group="ocr",
        palette_title=("多张图片合成一个可搜索 PDF", "Images into one searchable PDF"),
        category=("文字识别", "Recognize text"), choices=_tool("One searchable PDF"),
        hint=("拖入几张图片就会识别并合成一个可搜索 PDF", "drop several images to get one searchable PDF"),
        keywords=("ocr", "识别", "合成", "合并", "searchable", "combine"), targets=("pdf",),
        requires=VISION,
    ),
    Action(
        "scan_pdf", "image", ("拉平成 PDF · 彩色", "Flatten to PDF · color"), "scan", "pdf", group="scan",
        palette_title=("拍的纸质文件拉平成 PDF", "Flatten photographed paper into a PDF"),
        category=("扫描矫正", "Scan"), choices=_tool("Scan to PDF"),
        hint=("拖入拍的纸质文件就会拉平成 PDF", "drop photos of paper documents to flatten them into PDFs"),
        keywords=("扫描", "矫正", "拉平", "文件", "scan", "document", "flatten", "paper"), targets=("pdf",),
        requires=VISION,
    ),
    Action(
        "scan_pdf_bw", "image", ("拉平成 PDF · 黑白", "Flatten to PDF · B&W"), "scan", "pdf", group="scan",
        palette_title=("纸质文件拉平成黑白 PDF", "Flatten paper into a black-and-white PDF"),
        category=("扫描矫正", "Scan"), choices=_tool("Scan to PDF B&W"),
        hint=("拖入拍的纸质文件就会拉平成黑白 PDF", "drop photos of paper documents for black-and-white PDFs"),
        keywords=("扫描", "黑白", "scan", "black", "white", "bw", "b&w"), targets=("pdf",),
        requires=VISION,
    ),
    Action(
        "scan_jpg", "image", ("拉平成 JPG · 彩色", "Flatten to JPG · color"), "scan", "image", group="scan",
        palette_title=("纸质文件拉平成 JPG", "Flatten paper into a JPG"),
        category=("扫描矫正", "Scan"), choices=_tool("Scan to JPG"),
        hint=("拖入拍的纸质文件就会拉平成 JPG", "drop photos of paper documents to flatten them into JPGs"),
        keywords=("扫描", "scan", "jpg", "jpeg"), targets=("jpg",),
        requires=VISION,
    ),
    Action(
        "scan_jpg_bw", "image", ("拉平成 JPG · 黑白", "Flatten to JPG · B&W"), "scan", "image", group="scan",
        palette_title=("纸质文件拉平成黑白 JPG", "Flatten paper into a black-and-white JPG"),
        category=("扫描矫正", "Scan"), choices=_tool("Scan to JPG B&W"),
        hint=("拖入拍的纸质文件就会拉平成黑白 JPG", "drop photos of paper documents for black-and-white JPGs"),
        keywords=("扫描", "黑白", "scan", "bw", "b&w", "jpg"), targets=("jpg",),
        requires=VISION,
    ),
    Action(
        "scan_one", "image", ("合成一个 PDF · 彩色", "One PDF · color"), "layers", "pdf", group="scan",
        palette_title=("多页纸质文件扫描成一个 PDF", "Scan several pages into one PDF"),
        category=("扫描矫正", "Scan"), choices=_tool("One scanned PDF"),
        hint=("拖入几张纸质文件的照片就会扫描成一个 PDF", "drop photos of several pages to scan them into one PDF"),
        keywords=("扫描", "合成", "合并", "scan", "combine", "pages"), targets=("pdf",),
        requires=VISION,
    ),
    Action(
        "scan_one_bw", "image", ("合成一个 PDF · 黑白", "One PDF · B&W"), "layers", "pdf", group="scan",
        palette_title=("多页纸质文件扫描成一个黑白 PDF", "Scan several pages into one B&W PDF"),
        category=("扫描矫正", "Scan"), choices=_tool("One scanned PDF B&W"),
        hint=("拖入几张纸质文件的照片就会扫描成一个黑白 PDF", "drop photos of several pages for one B&W PDF"),
        keywords=("扫描", "黑白", "合成", "scan", "bw", "b&w"), targets=("pdf",),
        requires=VISION,
    ),
    Action(
        "faces_blur", "image", ("模糊", "Blur"), "face", "image", group="faces",
        palette_title=("人脸打码 · 模糊", "Blur faces"),
        category=("人脸打码", "Hide faces"), choices=_tool("Blur faces"),
        hint=("拖入照片就会把人脸模糊掉", "drop photos and every face is blurred"),
        keywords=("人脸", "打码", "模糊", "隐私", "face", "blur", "privacy"),
        requires=VISION,
    ),
    Action(
        "faces_pixelate", "image", ("马赛克", "Pixelate"), "face", "image", group="faces",
        palette_title=("人脸打码 · 马赛克", "Pixelate faces"),
        category=("人脸打码", "Hide faces"), choices=_tool("Pixelate faces"),
        hint=("拖入照片就会给人脸打上马赛克", "drop photos and every face is pixelated"),
        keywords=("人脸", "打码", "马赛克", "隐私", "face", "pixelate", "mosaic", "privacy"),
        requires=VISION,
    ),
    Action(
        "id_white", "image", ("白底", "White"), "id-card", "image", group="id_photo",
        palette_title=("证件照换白底", "ID photo · white background"),
        category=("证件照", "ID photo"), choices=_tool("ID photo white"),
        hint=("拖入人像照片就会换成白底", "drop a portrait to put it on white"),
        keywords=("证件照", "换底", "白底", "白色", "id", "passport", "white", "背景"),
        requires=VISION,
    ),
    Action(
        "id_blue", "image", ("蓝底", "Blue"), "id-card", "image", group="id_photo",
        palette_title=("证件照换蓝底", "ID photo · blue background"),
        category=("证件照", "ID photo"), choices=_tool("ID photo blue"),
        hint=("拖入人像照片就会换成蓝底", "drop a portrait to put it on blue"),
        keywords=("证件照", "换底", "蓝底", "蓝色", "id", "passport", "blue", "背景"),
        requires=VISION,
    ),
    Action(
        "id_red", "image", ("红底", "Red"), "id-card", "image", group="id_photo",
        palette_title=("证件照换红底", "ID photo · red background"),
        category=("证件照", "ID photo"), choices=_tool("ID photo red"),
        hint=("拖入人像照片就会换成红底", "drop a portrait to put it on red"),
        keywords=("证件照", "换底", "红底", "红色", "id", "passport", "red", "背景"),
        requires=VISION,
    ),
    *(
        Action(
            f"crop_{ratio.replace(':', 'x')}", "image", (ratio, ratio), "crop", "image", group="crop",
            palette_title=(f"智能裁剪 {ratio}", f"Smart crop {ratio}"),
            category=("智能裁剪", "Smart crop"), choices=_tool(f"Smart crop {ratio}"),
            hint=(f"拖入照片就会围绕主体裁成 {ratio}", f"drop photos to crop them to {ratio} around the subject"),
            keywords=("裁剪", "裁切", "比例", "crop", "ratio", "square" if ratio == "1:1" else "", ratio),
            requires=VISION,
        )
        for ratio in ("1:1", "4:5", "16:9", "9:16")
    ),
    Action(
        "triage", "image", ("挑出模糊和重复", "Find blurry & duplicates"), "images", "image",
        palette_title=("挑出模糊和重复的照片", "Find blurry and duplicate photos"),
        category=("照片整理", "Photo review"), choices=_tool("Blurry & duplicates"),
        hint=("拖入一批照片就会挑出模糊和重复的", "drop a batch of photos to sort out blurry and duplicate shots"),
        keywords=("模糊", "重复", "整理", "相似", "blurry", "duplicate", "similar", "cleanup"),
        requires=VISION,
    ),
    Action(
        "straighten", "image", ("自动扶正", "Straighten"), "level", "image", group="photo_more",
        category=("照片工具", "Photo tools"), choices=_tool("Straighten"),
        hint=("拖入歪的照片就会自动扶正", "drop tilted photos to level them"),
        keywords=("扶正", "水平", "歪", "旋转", "straighten", "level", "horizon", "rotate"),
        requires=VISION,
    ),
    Action(
        "enhance", "image", ("一键增强", "Auto enhance"), "wand", "image", group="photo_more",
        category=("照片工具", "Photo tools"), choices=_tool("Auto enhance"),
        hint=("拖入照片就会自动调好亮度和颜色", "drop photos to fix their light and color"),
        keywords=("增强", "调色", "美化", "enhance", "auto", "fix", "color"),
        requires=VISION,
    ),
    Action(
        "read_codes", "image", ("识别二维码和条码", "Read QR codes & barcodes"), "qr-code", "data", group="photo_more",
        category=("识别", "Recognize"), choices=_tool("Read codes"),
        hint=("拖入有二维码的图片就会读出内容", "drop images with QR codes to read them"),
        keywords=("二维码", "条码", "扫码", "qr", "barcode", "code"), targets=("txt",),
        requires=VISION,
    ),
    Action(
        "codes_csv", "image", ("二维码汇总成 CSV", "All codes into one CSV"), "qr-code", "data", group="photo_more",
        palette_title=("把多张图片里的二维码汇总成 CSV", "Collect QR codes from many images into a CSV"),
        category=("识别", "Recognize"), choices=_tool("Codes CSV"),
        hint=("拖入几张有二维码的图片就会汇总成一个 CSV", "drop images with QR codes to collect them into one CSV"),
        keywords=("二维码", "条码", "汇总", "qr", "barcode", "csv"), targets=("csv",),
        requires=VISION,
    ),
    *(
        Action(
            f"upscale_{style}_{scale}", "image", (f"{zh}放大 {scale}×", f"Upscale {en.lower()} {scale}×"),
            "sparkles", "image", group="photo_more",
            category=("图片 · AI", "Images · AI"),
            choices=_ai(MediaKind.IMAGE, f"Upscale {en} {scale}×"),
            hint=(f"拖入{zh}就会放大到 {scale} 倍", f"drop {en.lower()}s to enlarge them {scale}×"),
            keywords=("放大", "高清", "超分", "upscale", "enlarge", "hd", "ai", f"{scale}x"),
            requires=OperationKind.UPSCALE,
        )
        for style, zh, en in (("photo", "照片", "Photo"), ("illustration", "插画", "Illustration"))
        for scale in (2, 4)
    ),
    # ── 音视频 ────────────────────────────────────────────────────────────
    Action(
        "video_gif", "av", ("视频转 GIF", "Video to GIF"), "film", "video",
        palette_title=("把视频转成动图 GIF", "Turn videos into animated GIFs"),
        category=("视频", "Video"), choices=((MediaKind.VIDEO, "Animated GIF"),),
        hint=("拖入视频就会转成动图", "drop videos to turn them into animated GIFs"),
        keywords=(*_CONVERT, "动图", "gif", "animated", "mov", "mp4"), targets=("gif",),
    ),
    Action(
        "separate_vocals", "av", ("分离人声", "Separate vocals"), "audio-lines", "audio",
        palette_title=("分离人声和伴奏", "Separate vocals and accompaniment"),
        category=("音频 · AI", "Audio · AI"),
        choices=_ai(MediaKind.AUDIO, "Separate Vocals"),
        hint=("拖入歌曲就会分出人声和伴奏", "drop songs to split vocals from the music"),
        keywords=("人声", "伴奏", "消音", "卡拉ok", "vocals", "karaoke", "instrumental", "stems", "ai"),
        requires=OperationKind.SEPARATE_VOCALS,
    ),
    *(
        Action(
            f"subtitles_{fmt.lower()}", "av", (zh, en), "captions", "video", group="subtitles",
            palette_title=(f"给视频或音频生成{zh_long}", f"Make {en_long} from videos or audio"),
            category=("语音 · ThunderTalk", "Speech · ThunderTalk"),
            choices=_tool(key),
            hint=(f"拖入视频或音频就会生成{zh_long}", f"drop videos or audio to get {en_long}"),
            keywords=("字幕", "听写", "转文字", "语音识别", "subtitle", "caption", "transcribe",
                      "speech to text", "asr", "thundertalk", fmt.lower()),
            targets=(fmt.lower(),),
            requires=THUNDERTALK,
        )
        for key, fmt, zh, en, zh_long, en_long in (
            ("Subtitles SRT", "SRT", "SRT 字幕", "SRT subtitles", " SRT 字幕", "SRT subtitles"),
            ("Subtitles VTT", "VTT", "VTT 字幕", "VTT subtitles", " VTT 字幕", "VTT subtitles"),
            ("Transcript TXT", "TXT", "文字稿", "Transcript", "文字稿", "a transcript"),
        )
    ),
    Action(
        "read_aloud", "av", ("朗读成音频", "Read aloud"), "audio-lines", "audio",
        palette_title=("把文字朗读成音频", "Read text aloud into audio"),
        category=("语音 · ThunderTalk", "Speech · ThunderTalk"),
        choices=_tool("Read aloud M4A"),
        hint=("拖入 TXT、Markdown、Word 或 PDF 就会朗读成音频",
              "drop TXT, Markdown, Word or PDF files to hear them read aloud"),
        keywords=("朗读", "配音", "语音合成", "读出来", "有声", "tts", "read aloud", "voice", "speak",
                  "text to speech", "thundertalk", "m4a"),
        targets=("m4a",),
        requires=THUNDERTALK,
    ),
    # ── 更多 ──────────────────────────────────────────────────────────────
    Action(
        "finder_action", "more", ("安装 Finder 右键操作…", "Install Finder Quick Action…"), "folder", "neutral",
        category=("集成", "Integrations"), command="settings:integrations",
        keywords=("finder", "访达", "右键", "快速操作", "quick action", "service", "集成"),
    ),
    # ── app commands: menu bar and ⌘K only ───────────────────────────────
    Action("add_files", "app", ("添加文件…", "Add Files…"), "plus", category=("文件", "File"),
           command="add_files", shortcut="Ctrl+O", in_tools=False,
           keywords=("打开", "选择", "导入", "open", "choose", "import")),
    Action("paste", "app", ("粘贴", "Paste"), "file", category=("文件", "File"),
           palette_title=("粘贴文件或图片", "Paste files or an image"),
           command="paste", shortcut="Ctrl+V", in_tools=False, keywords=("剪贴板", "clipboard")),
    Action("clear", "app", ("清空", "Clear"), "trash", category=("文件", "File"),
           palette_title=("清空文件列表", "Clear the file list"),
           command="clear", shortcut="Ctrl+Backspace", in_tools=False,
           keywords=("删除", "移除", "remove", "delete", "empty")),
    Action("start", "app", ("开始转换", "Convert"), "arrow-right", "image", category=("文件", "File"),
           command="start", in_tools=False, keywords=("开始", "转换", "start", "go", "run")),
    Action("reveal", "app", ("在访达中显示结果", "Show Results in Finder"), "folder", category=("文件", "File"),
           command="reveal", in_tools=False, keywords=("访达", "finder", "打开", "results", "output")),
    Action("settings", "app", ("设置…", "Settings…"), "gear", category=("设置", "Settings"),
           palette_title=("打开设置", "Open Settings"), command="settings:general", shortcut="Ctrl+,",
           in_tools=False, keywords=("偏好", "preferences", "options", "选项")),
    Action("settings_appearance", "app", ("外观设置", "Appearance settings"), "contrast", category=("设置", "Settings"),
           command="settings:appearance", in_tools=False, keywords=("主题", "theme", "语言", "language")),
    Action("settings_convert", "app", ("转换设置", "Conversion settings"), "convert", category=("设置", "Settings"),
           palette_title=("转换设置 · 保存位置和默认格式", "Conversion settings · save location & formats"),
           command="settings:convert", in_tools=False,
           keywords=("保存位置", "默认格式", "命名", "destination", "default format", "naming", "folder")),
    Action("settings_components", "app", ("组件和 AI 模型", "Components & AI models"), "package",
           category=("设置", "Settings"), command="settings:components", in_tools=False,
           keywords=("下载", "模型", "组件", "download", "model", "libreoffice", "calibre", "ai")),
    Action("appearance_system", "app", ("外观：跟随系统", "Appearance: System"), "contrast",
           category=("外观", "Appearance"), command="appearance:system", in_tools=False,
           keywords=("主题", "自动", "theme", "auto", "system")),
    Action("appearance_light", "app", ("外观：浅色", "Appearance: Light"), "sun",
           category=("外观", "Appearance"), command="appearance:light", in_tools=False,
           keywords=("浅色模式", "亮色", "白天", "theme", "light mode")),
    Action("appearance_dark", "app", ("外观：深色", "Appearance: Dark"), "moon",
           category=("外观", "Appearance"), command="appearance:dark", in_tools=False,
           keywords=("深色模式", "暗色", "夜间", "黑色", "theme", "dark mode", "night")),
    Action("reduce_motion", "app", ("减少动效", "Reduce Motion"), "sparkles",
           category=("外观", "Appearance"), command="reduce_motion", in_tools=False,
           keywords=("动画", "动效", "倾斜", "animation", "motion", "tilt")),
    Action("shortcuts", "app", ("快捷键", "Keyboard Shortcuts"), "keyboard", category=("帮助", "Help"),
           command="shortcuts", in_tools=False, keywords=("键盘", "keyboard", "hotkey", "help")),
    Action("privacy", "app", ("隐私说明", "Privacy"), "lock", category=("帮助", "Help"),
           command="privacy", in_tools=False, keywords=("隐私", "本地", "privacy", "local", "offline")),
    Action("updates", "app", ("检查更新…", "Check for Updates…"), "download", category=("Wemute", "Wemute"),
           command="updates", requires=UPDATER, in_tools=False, keywords=("更新", "升级", "update", "upgrade")),
    Action("about", "app", ("关于 Wemute", "About Wemute"), "info", category=("Wemute", "Wemute"),
           command="settings:about", in_tools=False, keywords=("版本", "version", "license", "许可证")),
)


def _format_actions() -> tuple[Action, ...]:
    """"把图片转成 JPEG": one action per kind and plain output format."""
    actions: list[Action] = []
    for kind in FORMAT_KINDS:
        noun_zh, noun_en = KIND_NOUNS[kind]
        drop_zh, drop_en = DROP_NOUNS[kind]
        for option in options_for(kind):
            label_zh, label_en = choice_label(option, "zh"), choice_label(option, "en")
            actions.append(
                Action(
                    f"format:{kind.value}:{option}",
                    "convert",
                    (label_zh, label_en),
                    "convert",
                    kind.value,
                    palette_title=(_spaced(f"把{noun_zh}转成{label_zh}"), f"Convert {noun_en} to {label_en}"),
                    category=(GROUP_LABELS["zh"][kind], GROUP_LABELS["en"][kind]),
                    choices=((kind, option),),
                    hint=(
                        _spaced(f"拖入{drop_zh}就会转成{label_zh}"),
                        f"drop {drop_en} to convert them to {label_en}",
                    ),
                    keywords=(*_CONVERT, *kind_keywords(kind)),
                    targets=tuple(
                        part for part in re.split(r"[^a-z0-9]+", option.lower()) if part
                    )[:1],
                    group=f"formats/{kind.value}",
                )
            )
    return tuple(actions)


ACTIONS: tuple[Action, ...] = (*_NAMED[:9], *_format_actions(), *_NAMED[9:])
ACTION_BY_ID: dict[str, Action] = {action.id: action for action in ACTIONS}
for _kind in FORMAT_KINDS:
    GROUPS[f"formats/{_kind.value}"] = ((GROUP_LABELS["zh"][_kind], GROUP_LABELS["en"][_kind]), "convert")


def hint_for(action: Action, language: str) -> str:
    """The notice when no matching files are open: "去背景 · 拖入照片就会抠出主体"."""
    if action.id.startswith("format:"):
        label = text(action.title, language)
        title = _spaced(f"转成{label}") if language == "zh" else f"To {label}"
    elif action.group and action.group != "pdf":
        # "红底" alone says little; "证件照换红底" does.
        title = text(action.palette_title or action.title, language)
    else:
        title = text(action.title, language)
    title = title.rstrip("…")
    hint = text(action.hint, language)
    if not hint:
        return title
    return f"{title} · {hint[0].upper() + hint[1:] if language != 'zh' else hint}"


def category_for(action: Action, language: str) -> str:
    if action.category:
        return text(action.category, language)
    return text(SECTIONS[action.section], language)


# ── availability ─────────────────────────────────────────────────────────

Availability = Callable[[Action], str]
"""``"" `` when the action can run now, "missing" when it needs a download,
"hidden" when this Mac cannot offer it."""


def availability(
    enabled_ai: set[OperationKind], vision: bool, updater: bool, thundertalk: bool = False
) -> Availability:
    def check(action: Action) -> str:
        if action.requires == VISION:
            return "" if vision else "hidden"
        if action.requires == THUNDERTALK:
            return "" if thundertalk else "needs_app"
        if action.requires == UPDATER:
            return "" if updater else "hidden"
        if isinstance(action.requires, OperationKind):
            return "" if action.requires in enabled_ai else "missing"
        return ""

    return check


# ── menus ────────────────────────────────────────────────────────────────


def _row(action: Action, language: str, state: str) -> dict[str, object]:
    return {
        "type": "action",
        "id": action.id,
        "label": text(action.title, language),
        "icon": action.icon,
        "tint": action.tint,
        "shortcut": action.shortcut,
        "available": state == "",
        "tag": TAGS.get(state, ""),
    }


# The i18n key of the small tag on rows that cannot run yet.
TAGS = {"missing": "needs_download", "needs_app": "needs_thundertalk"}


def menu_tree(
    language: str,
    check: Availability,
    sections: Iterable[str] = TOOL_SECTIONS,
) -> list[dict[str, object]]:
    """Sections as ``header`` rows followed by actions and nested ``menu`` rows."""
    rows: list[dict[str, object]] = []
    for section in sections:
        items: list[dict[str, object]] = []
        menus: dict[str, dict[str, object]] = {}
        for action in ACTIONS:
            if action.section != section or not action.in_tools:
                continue
            state = check(action)
            if state == "hidden":
                continue
            container = items
            path = ""
            for part in action.group.split("/") if action.group else ():
                path = f"{path}/{part}" if path else part
                menu = menus.get(path)
                if menu is None:
                    title, icon = GROUPS[path]
                    menu = {"type": "menu", "id": path, "label": text(title, language), "icon": icon, "children": []}
                    menus[path] = menu
                    container.append(menu)
                container = menu["children"]  # type: ignore[assignment]
            container.append(_row(action, language, state))
        if items:
            rows.append({"type": "header", "label": text(SECTIONS[section], language)})
            rows.extend(items)
    return rows


# ── search ───────────────────────────────────────────────────────────────

_TOKEN = re.compile(rf"[{_CJK}]+|[^\s{_CJK}]+")


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).lower()


def query_tokens(query: str) -> list[str]:
    """"转pdf" → ["转", "pdf"]: Chinese and Latin runs split apart."""
    return _TOKEN.findall(_normalize(query))


def _subsequence(needle: str, haystack: str) -> bool:
    position = 0
    for char in needle:
        position = haystack.find(char, position) + 1
        if position == 0:
            return False
    return True


def _covered(action: Action) -> bool:
    """A per-format action that a named action already offers, e.g. 视频转 GIF."""
    if not action.id.startswith("format:"):
        return False
    return any(
        named.choices == action.choices and named.in_palette for named in _NAMED
    )


def palette_actions(check: Availability) -> list[Action]:
    return [
        action
        for action in ACTIONS
        if action.in_palette and not _covered(action) and check(action) != "hidden"
    ]


def _score(action: Action, tokens: list[str], compact: str, language: str) -> float | None:
    other = "en" if language == "zh" else "zh"
    primary = _normalize(text(action.palette_title or action.title, language))
    secondary = " ".join(
        _normalize(value)
        for value in (
            text(action.palette_title or action.title, other),
            *action.title,
        )
    )
    category = " ".join(_normalize(value) for value in (action.category or SECTIONS[action.section]))
    keywords = [_normalize(value) for value in action.keywords if value]
    total = 0.0
    for token in tokens:
        if token in primary:
            index = primary.find(token)
            total += 10 + (3 if index == 0 or primary[index - 1] in " ·（(" else 0)
        elif token in secondary:
            total += 7
        elif any(token == keyword for keyword in keywords):
            total += 7
        elif any(token in keyword for keyword in keywords):
            total += 5
        elif token in category:
            total += 4
        elif len(token) >= 2 and _subsequence(token, primary.replace(" ", "")):
            total += 2
        else:
            return None
        if token in action.targets:
            total += 4
    if compact and compact in primary.replace(" ", ""):
        total += 6
    return total - len(primary) * 0.04


def search(query: str, language: str, check: Availability, limit: int = 40) -> list[Action]:
    candidates = palette_actions(check)
    tokens = query_tokens(query)
    if not tokens:
        featured = [action for action in candidates if action.section != "app" and not action.id.startswith("format:")]
        return featured[:limit]
    compact = "".join(tokens)
    scored: list[tuple[float, int, Action]] = []
    for order, action in enumerate(candidates):
        score = _score(action, tokens, compact, language)
        if score is None:
            continue
        if check(action) in TAGS:
            score -= 1.5
        scored.append((score, order, action))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [action for _score_value, _order, action in scored[:limit]]
