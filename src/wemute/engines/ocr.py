"""Text recognition with Apple Vision: plain text, Word, and searchable PDFs."""

from __future__ import annotations

import io
import re
import statistics
import tempfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from wemute.engines.common import Reporter
from wemute.engines.vision_io import load_photo, perform, pil_to_cgimage

OCR_LANGUAGES = ["zh-Hans", "zh-Hant", "en-US", "ja-JP", "ko-KR"]
# Pages with at least this much real text are kept as they are.
TEXT_PAGE_MIN_CHARS = 24
OCR_DPI = 300

_CJK = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef\uac00-\ud7af\u3040-\u30ff]")
_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")
_KANA = re.compile(r"[\u3040-\u30ff]")
_HAN = re.compile(r"[\u4e00-\u9fff]")
_TOKEN = re.compile(
    r"[\u2e80-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef\uac00-\ud7af\u3040-\u30ff]"
    r"|[^\s\u2e80-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef\uac00-\ud7af\u3040-\u30ff]+"
)
_TRADITIONAL = set("們國會說時點這對過還進開關門問員錢體學實發經見長車東書與為頭電話號碼據證協議價機總應從後當幾樣灣廣葉華護廳務")
_SIMPLIFIED = set("们国会说时点这对过还进开关门问员钱体学实发经见长车东书与为头电话号码据证协议价机总应从后当几样湾广叶华护厅务")

Point = tuple[float, float]


@dataclass
class Token:
    text: str
    # Normalised corners, origin bottom-left: bottom-left, bottom-right, top-right, top-left.
    quad: tuple[Point, Point, Point, Point]
    space_after: bool = False


@dataclass
class Line:
    text: str
    quad: tuple[Point, Point, Point, Point]
    tokens: list[Token] = field(default_factory=list)

    def box(self, width: float, height: float) -> tuple[float, float, float, float]:
        """Axis-aligned box in pixels, origin top-left: x0, y0, x1, y1."""
        xs = [point[0] * width for point in self.quad]
        ys = [(1 - point[1]) * height for point in self.quad]
        return min(xs), min(ys), max(xs), max(ys)


def _corners(observation) -> tuple[Point, Point, Point, Point]:  # noqa: ANN001
    points = (
        observation.bottomLeft(),
        observation.bottomRight(),
        observation.topRight(),
        observation.topLeft(),
    )
    return tuple((float(point.x), float(point.y)) for point in points)  # type: ignore[return-value]


def _utf16_ranges(text: str) -> list[tuple[str, int, int, int]]:
    """Tokens (CJK characters one by one, other runs as words): text, index, UTF-16 range."""
    tokens: list[tuple[str, int, int, int]] = []
    for match in _TOKEN.finditer(text):
        start = len(text[: match.start()].encode("utf-16-le")) // 2
        length = len(match.group().encode("utf-16-le")) // 2
        tokens.append((match.group(), match.start(), start, length))
    return tokens


def _lerp(a: Point, b: Point, t: float) -> Point:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _split_quad(line: tuple[Point, Point, Point, Point], start: float, end: float):  # noqa: ANN202
    bl, br, tr, tl = line
    return (_lerp(bl, br, start), _lerp(bl, br, end), _lerp(tl, tr, end), _lerp(tl, tr, start))


def _weight(text: str) -> float:
    return sum(1.0 if _CJK.match(char) else 0.3 if char == " " else 0.55 for char in text)


def _line_tokens(candidate, text: str, quad) -> list[Token]:  # noqa: ANN001
    tokens: list[Token] = []
    total = _weight(text) or 1.0
    for token_text, index, start, length in _utf16_ranges(text):
        box = None
        try:
            observation, _error = candidate.boundingBoxForRange_error_((start, length), None)
            if observation is not None:
                corners = _corners(observation)
                xs = [point[0] for point in corners]
                if max(xs) - min(xs) > 1e-5:
                    box = corners
        except Exception:  # noqa: BLE001 - fall back to proportional placement
            box = None
        if box is None:
            offset = _weight(text[:index]) / total
            box = _split_quad(quad, offset, min(1.0, offset + _weight(token_text) / total))
        following = text[index + len(token_text) : index + len(token_text) + 1]
        tokens.append(Token(token_text, box, following.isspace()))
    return tokens


def _script_passes(text: str) -> list[list[str]]:
    """Focused language sets for every script a first auto-detected pass saw.

    Vision reads one language family at a time best: a mixed Japanese and
    Korean page read as Japanese turns the Korean lines into noise.
    """
    passes: list[list[str]] = []
    if len(_HANGUL.findall(text)) >= 2:
        passes.append(["ko-KR", "en-US"])
    if len(_KANA.findall(text)) >= 2:
        passes.append(["ja-JP", "en-US"])
    han = len(_HAN.findall(text))
    if han >= 2 and han > len(_KANA.findall(text)):
        traditional = sum(char in _TRADITIONAL for char in text)
        simplified = sum(char in _SIMPLIFIED for char in text)
        if traditional > simplified:
            passes.append(["zh-Hant", "zh-Hans", "en-US"])
        else:
            passes.append(["zh-Hans", "zh-Hant", "en-US"])
    return passes


def _recognize_pass(cg_image, languages: list[str], automatic: bool):  # noqa: ANN001, ANN202
    import Vision

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)
    request.setRecognitionLanguages_(languages)
    if request.respondsToSelector_("setAutomaticallyDetectsLanguage:"):
        request.setAutomaticallyDetectsLanguage_(automatic)
    perform(cg_image, [request])
    results = []
    for observation in request.results() or []:
        candidates = observation.topCandidates_(1)
        if candidates and candidates[0].string().strip():
            results.append((observation, candidates[0]))
    return results


Quad = tuple[Point, Point, Point, Point]


def _inside(point: Point, quad: Quad) -> bool:
    """Whether ``point`` lies in a convex quad (corners in order)."""
    signs = []
    for index in range(4):
        (x0, y0), (x1, y1) = quad[index], quad[(index + 1) % 4]
        signs.append((x1 - x0) * (point[1] - y0) - (y1 - y0) * (point[0] - x0) >= 0)
    return all(signs) or not any(signs)


def _centre(quad: Quad) -> Point:
    return sum(point[0] for point in quad) / 4, sum(point[1] for point in quad) / 4


def _same_line(a: Quad, b: Quad) -> bool:
    """Two readings of one line: each centre falls inside the other's rotated box.
    Axis-aligned boxes would merge neighbouring lines on a tilted page."""
    return _inside(_centre(a), b) and _inside(_centre(b), a)


def _merge_passes(passes: list[list]) -> list:  # noqa: ANN001
    """One reading per line region: the most confident pass wins (later, more
    focused passes win ties); lines only one pass found are kept when credible."""
    chosen: list[tuple[Quad, float, tuple]] = []
    for order, results in enumerate(passes):
        for item in results:
            rect = _corners(item[0])
            confidence = float(item[1].confidence())
            overlapping = [index for index, (other, _c, _i) in enumerate(chosen) if _same_line(rect, other)]
            if not overlapping:
                if order == 0 or confidence >= 0.45:
                    chosen.append((rect, confidence, item))
                continue
            best = max(chosen[index][1] for index in overlapping)
            # CJK recognizers report a flat 0.5, so a Latin misreading of CJK
            # glyphs ("季度报告" → "ZEE") would always look more confident.
            recovers_cjk = order > 0 and len(_CJK.findall(str(item[1].string()))) >= 2 and not any(
                _CJK.search(str(chosen[index][2][1].string())) for index in overlapping
            )
            if confidence >= best or recovers_cjk:
                for index in sorted(overlapping, reverse=True):
                    chosen.pop(index)
                chosen.append((rect, confidence, item))
    chosen.sort(key=lambda entry: (-_centre(entry[0])[1], _centre(entry[0])[0]))
    return [item for _quad, _confidence, item in chosen]


def recognize(image: Image.Image) -> list[Line]:
    """Lines of text in reading order, with per-word / per-character boxes."""
    cg_image = pil_to_cgimage(image)
    results = _recognize_pass(cg_image, OCR_LANGUAGES, True)
    joined = "\n".join(candidate.string() for _observation, candidate in results)
    focused = [_recognize_pass(cg_image, languages, False) for languages in _script_passes(joined)]
    if focused:
        results = _merge_passes([results, *focused])
    lines: list[Line] = []
    for observation, candidate in results:
        text = str(candidate.string()).strip()
        quad = _corners(observation)
        lines.append(Line(text, quad, _line_tokens(candidate, text, quad)))
    return lines


# ── reading order and paragraphs ─────────────────────────────────────────


def _ends_cjk(text: str) -> bool:
    return bool(text) and bool(_CJK.match(text[-1]))


def _starts_cjk(text: str) -> bool:
    return bool(text) and bool(_CJK.match(text[0]))


def _join(previous: str, following: str) -> str:
    if previous.endswith("-") and following[:1].islower():
        return previous[:-1] + following
    if _ends_cjk(previous) or _starts_cjk(following):
        return previous + following
    return f"{previous} {following}"


@dataclass
class Paragraph:
    lines: list[str]
    heading: bool = False

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


Box = tuple[float, float, float, float]
Piece = tuple[Box, str]


def _deskewed_boxes(lines: list[Line], width: float, height: float) -> list[Piece]:
    """Line boxes measured along the page's dominant text direction."""
    import math

    angles = []
    for line in lines:
        bl, br, _tr, tl = line.quad
        dx, dy = (br[0] - bl[0]) * width, (br[1] - bl[1]) * height
        tall = math.hypot((tl[0] - bl[0]) * width, (tl[1] - bl[1]) * height)
        if math.hypot(dx, dy) > 3 * tall:
            angles.append(math.atan2(dy, dx))
    angle = statistics.median(angles) if angles else 0.0
    cos, sin = math.cos(-angle), math.sin(-angle)
    pieces: list[Piece] = []
    for line in lines:
        xs, ys = [], []
        for u, v in line.quad:
            x, y = (u - 0.5) * width, (v - 0.5) * height
            xs.append(x * cos - y * sin + width / 2)
            ys.append(height / 2 - (x * sin + y * cos))
        pieces.append(((min(xs), min(ys), max(xs), max(ys)), line.text))
    return pieces


def _merge(pieces: list[Piece]) -> Piece:
    pieces = sorted(pieces, key=lambda item: item[0][0])
    text = pieces[0][1]
    for (previous_box, _), (box, piece) in zip(pieces, pieces[1:]):
        gap = box[0] - previous_box[2]
        if gap > 2.5 * (previous_box[3] - previous_box[1]):
            separator = "\t"
        else:
            separator = "" if _ends_cjk(text) and _starts_cjk(piece) else " "
        text += separator + piece
    box = (
        min(item[0][0] for item in pieces),
        min(item[0][1] for item in pieces),
        max(item[0][2] for item in pieces),
        max(item[0][3] for item in pieces),
    )
    return box, text


def _column_split(row: list[Piece], width: float) -> float | None:
    """The x of a wide gutter splitting a row into two real columns, if any."""
    row = sorted(row, key=lambda item: item[0][0])
    for index in range(1, len(row)):
        left, right = row[:index], row[index:]
        gap = right[0][0][0] - max(item[0][2] for item in left)
        left_width = max(item[0][2] for item in left) - left[0][0][0]
        right_width = max(item[0][2] for item in right) - right[0][0][0]
        if gap > 0.08 * width and min(left_width, right_width) > 0.18 * width:
            return (max(item[0][2] for item in left) + right[0][0][0]) / 2
    return None


def _reading_order(lines: list[Line], width: float, height: float) -> list[Piece]:
    """Visual lines top to bottom; two-column sections read left column first."""
    pieces = sorted(_deskewed_boxes(lines, width, height), key=lambda item: (item[0][1] + item[0][3]) / 2)
    rows: list[list[Piece]] = []
    for box, text in pieces:
        if rows:
            last = rows[-1]
            top = min(item[0][1] for item in last)
            bottom = max(item[0][3] for item in last)
            overlap = min(bottom, box[3]) - max(top, box[1])
            if overlap > 0.55 * min(bottom - top, box[3] - box[1]):
                last.append((box, text))
                continue
        rows.append([(box, text)])

    ordered: list[Piece] = []
    index = 0
    while index < len(rows):
        split = _column_split(rows[index], width)
        if split is None and index + 1 < len(rows) and len(rows[index]) > 1:
            # A row of short column titles belongs to the columns under it.
            following = _column_split(rows[index + 1], width)
            if following is not None and all(
                item[0][2] <= following or item[0][0] >= following for item in rows[index]
            ):
                split = following
        if split is None:
            ordered.append(_merge(rows[index]))
            index += 1
            continue
        left: list[Piece] = []
        right: list[Piece] = []
        end = index
        while end < len(rows):
            row = rows[end]
            if any(item[0][0] < split < item[0][2] for item in row):
                break
            row_left = [item for item in row if item[0][2] <= split]
            row_right = [item for item in row if item[0][0] >= split]
            if row_left:
                left.append(_merge(row_left))
            if row_right:
                right.append(_merge(row_right))
            end += 1
        ordered.extend(left + right)
        index = end
    return ordered


def paragraphs(lines: list[Line], width: float = 1000.0, height: float = 1000.0) -> list[Paragraph]:
    """Group recognised lines into paragraphs; wrapped lines are joined."""
    rows = _reading_order(lines, width, height)
    if not rows:
        return []
    heights = [box[3] - box[1] for box, _ in rows]
    typical = statistics.median(heights)
    right_edge = max(box[2] for box, _ in rows)
    result: list[Paragraph] = []
    current: list[str] = []
    previous_box = None
    heading = False
    for box, text in rows:
        line_height = box[3] - box[1]
        is_heading = line_height > 1.45 * typical and len(text) < 80
        if previous_box is not None:
            gap = box[1] - previous_box[3]
            previous_height = previous_box[3] - previous_box[1]
            size_jump = line_height > 1.3 * previous_height or line_height < 0.77 * previous_height
            column_jump = abs(box[0] - previous_box[0]) > 4 * typical and (
                box[0] > previous_box[2] or box[2] < previous_box[0]
            )
            if gap > 0.7 * max(typical, min(previous_height, line_height)) or size_jump or column_jump or is_heading or heading:
                result.append(Paragraph(current, heading))
                current = []
        if current:
            previous_text = current[-1]
            full = previous_box[2] >= 0.86 * right_edge and previous_box[0] <= box[0] + typical
            terminal = previous_text[-1:] in set("。！？.!?:：;；")
            if full and not terminal and "\t" not in previous_text and "\t" not in text:
                current[-1] = _join(previous_text, text)
            else:
                current.append(text)
        else:
            current = [text]
        heading = is_heading
        previous_box = box
    if current:
        result.append(Paragraph(current, heading))
    return result


def plain_text(groups: list[list[Paragraph]]) -> str:
    """Pages separated by form feeds, paragraphs by blank lines."""
    pages = ["\n\n".join(paragraph.text for paragraph in page) for page in groups]
    return "\n\n\f".join(page for page in pages).strip() + "\n"


def write_docx(groups: list[list[Paragraph]], output: Path) -> None:
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.oxml.ns import qn
    from docx.shared import Pt

    document = Document()
    normal = document.styles["Normal"]
    normal.font.size = Pt(11)
    fonts = normal.element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:eastAsia"), "PingFang SC")
    for page_index, page in enumerate(groups):
        if page_index:
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        for paragraph in page:
            if paragraph.heading:
                document.add_heading(" ".join(paragraph.lines), level=1)
                continue
            block = document.add_paragraph()
            for index, text in enumerate(paragraph.lines):
                run = block.add_run(text.replace("\t", "    "))
                if index < len(paragraph.lines) - 1:
                    run.add_break()
    document.save(str(output))


# ── invisible text layer ─────────────────────────────────────────────────

_FONT_NAME = "/WemuteOCR"
_ASCENT, _DESCENT, _ADVANCE = 800, -200, 500
# Glyph widths match ``_weight`` so a run of characters spans its real width:
# viewers neither invent spaces inside words nor drop overlapping glyphs.
_LATIN_WIDTH, _SPACE_WIDTH, _CJK_WIDTH = 550, 300, 1000
_WIDTHS = [
    0x20, 0x20, _SPACE_WIDTH,
    0x2E80, 0x9FFF, _CJK_WIDTH,
    0xAC00, 0xD7AF, _CJK_WIDTH,
    0xF900, 0xFAFF, _CJK_WIDTH,
    0xFF00, 0xFFEF, _CJK_WIDTH,
]


def _glyphless_font() -> bytes:
    """A TrueType font whose glyphs are empty; text drawn with it is invisible
    but selectable, and every code maps to one 500-unit-wide glyph."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "blank"])
    builder.setupCharacterMap({0x20: "blank"})
    empty = TTGlyphPen(None).glyph()
    builder.setupGlyf({".notdef": empty, "blank": empty})
    builder.setupHorizontalMetrics({".notdef": (_ADVANCE, 0), "blank": (_ADVANCE, 0)})
    builder.setupHorizontalHeader(ascent=_ASCENT, descent=_DESCENT)
    builder.setupNameTable({"familyName": "WemuteOCR", "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=_ASCENT, sTypoDescender=_DESCENT, usWinAscent=_ASCENT, usWinDescent=-_DESCENT)
    builder.setupPost()
    buffer = io.BytesIO()
    builder.save(buffer)
    return buffer.getvalue()


def _to_unicode_cmap() -> bytes:
    ranges = [f"<{high:02X}00> <{high:02X}FF> <{high:02X}00>" for high in range(256) if not 0xD8 <= high <= 0xDF]
    blocks = []
    for start in range(0, len(ranges), 100):
        chunk = ranges[start : start + 100]
        blocks.append(f"{len(chunk)} beginbfrange\n" + "\n".join(chunk) + "\nendbfrange")
    return (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
        "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
        + "\n".join(blocks)
        + "\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    ).encode("ascii")


def ocr_font(pdf):  # noqa: ANN001, ANN201 - pikepdf objects
    """The Type0 font for invisible text, shared by every page of ``pdf``."""
    import pikepdf
    from pikepdf import Array, Dictionary, Name

    font_file = pikepdf.Stream(pdf, _glyphless_font())
    cid_to_gid = pikepdf.Stream(pdf, zlib.compress(b"\x00\x01" * 65536, 9))
    cid_to_gid.Filter = Name.FlateDecode
    descriptor = Dictionary(
        Type=Name.FontDescriptor,
        FontName=Name("/WemuteOCR"),
        Flags=4,
        FontBBox=Array([0, _DESCENT, _ADVANCE, _ASCENT]),
        ItalicAngle=0,
        Ascent=_ASCENT,
        Descent=_DESCENT,
        CapHeight=_ASCENT,
        StemV=80,
        FontFile2=font_file,
    )
    cid_font = Dictionary(
        Type=Name.Font,
        Subtype=Name.CIDFontType2,
        BaseFont=Name("/WemuteOCR"),
        CIDSystemInfo=Dictionary(Registry="Adobe", Ordering="Identity", Supplement=0),
        FontDescriptor=pdf.make_indirect(descriptor),
        DW=_LATIN_WIDTH,
        W=Array(_WIDTHS),
        CIDToGIDMap=cid_to_gid,
    )
    font = Dictionary(
        Type=Name.Font,
        Subtype=Name.Type0,
        BaseFont=Name("/WemuteOCR"),
        Encoding=Name("/Identity-H"),
        DescendantFonts=Array([pdf.make_indirect(cid_font)]),
        ToUnicode=pikepdf.Stream(pdf, _to_unicode_cmap()),
    )
    return pdf.make_indirect(font)


def _code_unit(char: str) -> int:
    code = ord(char)
    return code if code <= 0xFFFF and not 0xD800 <= code <= 0xDFFF else 0xFFFD


def _line_runs(line: Line, transform):  # noqa: ANN001, ANN202
    """Baseline frame of a line and every token's start/end along it, in points."""
    import math

    bl, br, _tr, tl = (transform(point) for point in line.quad)
    dx, dy = br[0] - bl[0], br[1] - bl[1]
    length = math.hypot(dx, dy)
    height = math.hypot(tl[0] - bl[0], tl[1] - bl[1])
    if length < 0.5 or height < 0.5:
        return None
    direction = (dx / length, dy / length)

    def along(point: Point) -> float:
        x, y = transform(point)
        return (x - bl[0]) * direction[0] + (y - bl[1]) * direction[1]

    runs: list[tuple[str, float, float]] = []
    tokens = line.tokens or [Token(line.text, line.quad)]
    for index, token in enumerate(tokens):
        positions = [along(point) for point in token.quad]
        start, end = max(0.0, min(positions)), min(length, max(positions))
        if end <= start:
            continue
        runs.append((token.text, start, end))
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        # Spaces between Latin words keep them apart when the text is copied.
        if following and (token.space_after or not (_ends_cjk(token.text) or _starts_cjk(following.text))):
            next_start = max(0.0, min(along(point) for point in following.quad))
            runs.append((" ", end, max(end, next_start)))
    origin = (
        bl[0] + (tl[0] - bl[0]) * (-_DESCENT / 1000),
        bl[1] + (tl[1] - bl[1]) * (-_DESCENT / 1000),
    )
    return origin, direction, height, runs


def text_layer(lines: list[Line], transform, font_name: str = _FONT_NAME) -> bytes:  # noqa: ANN001
    """Content stream drawing each line invisibly over where it was recognised.

    One text object per line keeps a shared baseline (viewers rebuild lines from
    it). Glyph widths follow the script, one horizontal scale fits the line, and
    TJ offsets move each word to its recognised start without ever overlapping
    the previous one. ``transform`` maps a normalised point (origin bottom-left)
    to page space.
    """
    parts = ["BT", "3 Tr"]
    for line in lines:
        frame = _line_runs(line, transform)
        if not frame:
            continue
        origin, (cos, sin), size, runs = frame
        words = [(text, start, end) for text, start, end in runs if text != " "]
        if not words:
            continue
        # A CJK character's box is narrower than its pitch; measuring it to the
        # next character keeps glyphs touching, so viewers add no false spaces.
        widths = []
        for index, (text, start, end) in enumerate(words):
            following = words[index + 1] if index + 1 < len(words) else None
            if following and _ends_cjk(text) and _starts_cjk(following[0]) and following[1] - end < 0.5 * size:
                end = max(end, following[1])
            widths.append(end - start)
        natural = sum(_weight(text) for text, _start, _end in words) * size
        scale = max(0.2, min(5.0, sum(widths) / natural))
        unit = size * scale  # points per 1000 font units / 1000
        first = runs[0][1]
        x = origin[0] + cos * first
        y = origin[1] + sin * first
        items = []
        position = first
        previous = ""
        for text, start, _end in runs:
            gap = start - position
            if _ends_cjk(previous) and _starts_cjk(text) and gap < 0.8 * size:
                gap = 0.0
            previous = text
            if gap > 0.01 * size:
                items.append(f"{-gap / unit * 1000:.1f}")
            else:
                start = position
            items.append("<" + "".join(f"{_code_unit(char):04X}" for char in text) + ">")
            position = start + _weight(text) * unit
        parts.append(
            f"{font_name} {size:.2f} Tf {scale * 100:.2f} Tz "
            f"{cos:.5f} {sin:.5f} {-sin:.5f} {cos:.5f} {x:.2f} {y:.2f} Tm "
            f"[{' '.join(items)}] TJ"
        )
    parts.append("ET")
    return ("\n".join(parts) + "\n").encode("ascii")


def add_image_page(pdf, font, image_stream: tuple, lines: list[Line]) -> None:  # noqa: ANN001
    """Append a page showing one image with its recognised text over it."""
    import pikepdf
    from pikepdf import Array, Dictionary, Name

    from wemute.engines.pdf import A4_LONG_EDGE_POINTS

    data, filter_name, width, height, colorspace = image_stream
    scale = A4_LONG_EDGE_POINTS / max(width, height)
    page_width, page_height = round(width * scale, 2), round(height * scale, 2)
    image = pikepdf.Stream(pdf, data)
    image.Type = Name.XObject
    image.Subtype = Name.Image
    image.Width = width
    image.Height = height
    image.ColorSpace = Name(colorspace)
    image.BitsPerComponent = 8
    image.Filter = Name(filter_name)
    layer = text_layer(lines, lambda point: (point[0] * page_width, point[1] * page_height))
    content = pikepdf.Stream(
        pdf, f"q {page_width} 0 0 {page_height} 0 0 cm /Im0 Do Q\n".encode("ascii") + layer
    )
    page = Dictionary(
        Type=Name.Page,
        MediaBox=Array([0, 0, page_width, page_height]),
        Resources=Dictionary(XObject=Dictionary(Im0=image), Font=Dictionary(WemuteOCR=font)),
        Contents=content,
    )
    pdf.pages.append(pikepdf.Page(page))


# ── jobs ─────────────────────────────────────────────────────────────────


def _recognize_file(source: Path, reporter: Reporter) -> tuple[Image.Image, list[Line]]:
    photo = load_photo(source, reporter)
    from wemute.engines.vision_io import flatten

    image = flatten(photo.image)
    return image, recognize(image)


def images_to_text(sources: list[Path], output: Path, target: str, reporter: Reporter) -> None:
    """TXT or DOCX from one image (or several, one page each)."""
    reporter.stage("stage_recognizing")
    pages: list[list[Paragraph]] = []
    for index, source in enumerate(sources):
        image, lines = _recognize_file(source, reporter)
        pages.append(paragraphs(lines, *image.size))
        reporter.progress(0.9 * (index + 1) / len(sources))
    if not any(pages):
        raise reporter.error("no_text")
    reporter.stage("stage_saving")
    if target == "docx":
        write_docx(pages, output)
    else:
        output.write_text(plain_text(pages), encoding="utf-8")
    reporter.progress(1.0)


def images_to_searchable_pdf(sources: list[Path], output: Path, reporter: Reporter) -> None:
    """Each image becomes a page with selectable, searchable text over it."""
    import pikepdf

    from wemute.engines.pdf import _image_page_stream

    reporter.stage("stage_recognizing")
    pdf = pikepdf.Pdf.new()
    font = ocr_font(pdf)
    found = False
    with tempfile.TemporaryDirectory(prefix="wemute-ocr-") as scratch:
        for index, source in enumerate(sources):
            _image, lines = _recognize_file(source, reporter)
            found = found or bool(lines)
            stream = _image_page_stream(source, Path(scratch), index, reporter)
            add_image_page(pdf, font, stream, lines)
            reporter.progress(0.92 * (index + 1) / len(sources))
    if not found:
        raise reporter.error("no_text")
    reporter.stage("stage_saving")
    pdf.save(output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    reporter.progress(1.0)


def _display_to_user(rotation: int, width: float, height: float, x0: float, y0: float):  # noqa: ANN202
    """Map a normalised point on the displayed (rotated) page to PDF user space."""

    def transform(point: Point) -> Point:
        u, v = point
        if rotation == 90:
            x, y = width * (1 - v), height * u
        elif rotation == 180:
            x, y = width * (1 - u), height * (1 - v)
        elif rotation == 270:
            x, y = width * v, height * (1 - u)
        else:
            x, y = width * u, height * v
        return x0 + x, y0 + y

    return transform


def _page_text(page) -> str:  # noqa: ANN001
    textpage = page.get_textpage()
    try:
        return textpage.get_text_range()
    finally:
        textpage.close()


def pdf_ocr(source: Path, output: Path, target: str, reporter: Reporter) -> None:
    """Searchable PDF (scanned pages gain a text layer) or text for every page."""
    import pikepdf

    from wemute.engines.pdf import _open_pdfium

    document = _open_pdfium(source, reporter)
    reporter.stage("stage_recognizing")
    count = len(document)
    if not count:
        raise reporter.error("no_pages")
    pdf = pikepdf.open(source) if target == "pdf" else None
    font = ocr_font(pdf) if pdf is not None else None
    texts: list[list[Paragraph]] = []
    recognised = 0
    try:
        for index in range(count):
            page = document[index]
            existing = _page_text(page)
            if len(existing.strip()) >= TEXT_PAGE_MIN_CHARS:
                texts.append([Paragraph([chunk]) for chunk in re.split(r"\n\s*\n", existing.replace("\r\n", "\n").strip()) if chunk.strip()])
            else:
                rendered = page.render(scale=OCR_DPI / 72).to_pil().convert("RGB")
                lines = recognize(rendered)
                recognised += 1
                texts.append(paragraphs(lines, *rendered.size))
                if pdf is not None and lines:
                    left, bottom, right, top = page.get_cropbox()
                    rotation = page.get_rotation() % 360
                    transform = _display_to_user(rotation, right - left, top - bottom, left, bottom)
                    target_page = pdf.pages[index]
                    name = target_page.add_resource(font, pikepdf.Name.Font, prefix="WemuteOCR")
                    target_page.contents_add(b"q\n", prepend=True)
                    target_page.contents_add(b"\nQ\n" + text_layer(lines, transform, str(name)))
            page.close()
            reporter.progress(0.92 * (index + 1) / count)
        if not any(texts):
            raise reporter.error("no_text")
        reporter.stage("stage_saving")
        if pdf is not None:
            pdf.save(output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        else:
            output.write_text(plain_text(texts), encoding="utf-8")
    finally:
        document.close()
        if pdf is not None:
            pdf.close()
    reporter.progress(1.0)

