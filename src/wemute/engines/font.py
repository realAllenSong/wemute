from __future__ import annotations

from pathlib import Path

from wemute.engines.common import ConversionError, Reporter

FLAVORS = {".ttf": None, ".otf": None, ".woff": "woff", ".woff2": "woff2"}
_TRUETYPE_ONLY = ("glyf", "loca", "fpgm", "prep", "cvt ", "gasp", "hdmx", "LTSH", "VDMX", "gvar", "cvar")


def _quadratic_glyphs(glyph_set, max_err: float = 1.0):  # noqa: ANN001, ANN202
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    glyphs = {}
    for name in glyph_set.keys():
        pen = TTGlyphPen(glyph_set)
        glyph_set[name].draw(Cu2QuPen(pen, max_err, reverse_direction=True))
        glyphs[name] = pen.glyph()
    return glyphs


def cff_to_truetype(font) -> None:  # noqa: ANN001
    """Cubic CFF outlines → quadratic TrueType outlines (fontTools' otf2ttf recipe)."""
    from fontTools.ttLib import newTable

    if "CFF2" in font:
        raise ConversionError("Variable CFF2 fonts cannot be converted to TrueType yet")
    glyph_order = font.getGlyphOrder()
    font["loca"] = newTable("loca")
    glyf = font["glyf"] = newTable("glyf")
    glyf.glyphOrder = glyph_order
    glyf.glyphs = _quadratic_glyphs(font.getGlyphSet())
    del font["CFF "]
    if "VORG" in font:
        del font["VORG"]
    glyf.compile(font)
    hmtx = font["hmtx"]
    for name, glyph in glyf.glyphs.items():
        if hasattr(glyph, "xMin"):
            hmtx[name] = (hmtx[name][0], glyph.xMin)
    maxp = font["maxp"] = newTable("maxp")
    maxp.tableVersion = 0x00010000
    for field in (
        "maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs",
        "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions",
    ):
        setattr(maxp, field, 1 if field == "maxZones" else 0)
    maxp.maxComponentElements = max(
        (len(getattr(glyph, "components", []) or []) for glyph in glyf.glyphs.values()), default=0
    )
    maxp.compile(font)
    post = font["post"]
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyph_order
    font["head"].glyphDataFormat = 0
    font.sfntVersion = "\x00\x01\x00\x00"


def truetype_to_cff(font) -> None:  # noqa: ANN001
    """Quadratic TrueType outlines → cubic CFF outlines."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.t2CharStringPen import T2CharStringPen

    if "gvar" in font or "fvar" in font:
        raise ConversionError("Variable TrueType fonts cannot be converted to OTF yet")
    glyph_order = font.getGlyphOrder()
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    charstrings = {}
    for name in glyph_order:
        pen = T2CharStringPen(hmtx[name][0], glyph_set)
        glyph_set[name].draw(pen)
        charstrings[name] = pen.getCharString()
    names = font["name"]
    ps_name = (names.getDebugName(6) or "Font").replace(" ", "")
    info = {
        "FullName": names.getDebugName(4) or ps_name,
        "FamilyName": names.getDebugName(1) or ps_name,
        "Weight": names.getDebugName(2) or "Regular",
    }
    for tag in _TRUETYPE_ONLY:
        if tag in font:
            del font[tag]
    builder = FontBuilder(font=font, isTTF=False)
    builder.setupCFF(ps_name, info, charstrings, {})
    font["maxp"].tableVersion = 0x00005000
    post = font["post"]
    post.formatType = 3.0
    font.sfntVersion = "OTTO"


def convert(source: Path, output: Path, extension: str, reporter: Reporter) -> None:
    from fontTools.ttLib import TTFont, TTLibError

    reporter.stage("stage_reading")
    try:
        font = TTFont(str(source), recalcBBoxes=True, recalcTimestamp=False)
        font.getGlyphOrder()
    except (TTLibError, OSError, AssertionError, KeyError) as exc:
        raise reporter.error("bad_font") from exc
    reporter.progress(0.2)
    is_cff = "CFF " in font or "CFF2" in font
    reporter.stage("stage_converting")
    if extension == ".ttf" and is_cff:
        cff_to_truetype(font)
    elif extension == ".otf" and not is_cff:
        truetype_to_cff(font)
    reporter.progress(0.7)
    font.flavor = FLAVORS[extension]
    reporter.stage("stage_saving")
    font.save(str(output))
    font.close()
    reporter.progress(1.0)
