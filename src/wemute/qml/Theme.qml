pragma Singleton
import QtQuick

// "Ice" — a soft glass panel floating on cool pastel glows. Kind colours:
// image = cobalt, video = teal, audio = violet. Follows the system appearance.
QtObject {
    id: theme
    readonly property bool dark: Application.styleHints.colorScheme === Qt.ColorScheme.Dark

    // Background and glass
    readonly property color base: dark ? "#0D1220" : "#F2F5FB"
    readonly property color glow1: dark ? Qt.rgba(61 / 255, 92 / 255, 1, 0.28) : "#DFE7FF"
    readonly property color glow2: dark ? Qt.rgba(20 / 255, 170 / 255, 150 / 255, 0.18) : "#D9F3EF"
    readonly property color glow3: dark ? Qt.rgba(120 / 255, 90 / 255, 1, 0.18) : "#E9E4FF"
    readonly property color panel: dark ? Qt.rgba(24 / 255, 30 / 255, 48 / 255, 0.66) : Qt.rgba(1, 1, 1, 0.72)
    readonly property color panelLine: dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(1, 1, 1, 0.9)
    readonly property color panelShadow: dark ? Qt.rgba(0, 0, 0, 0.7) : Qt.rgba(40 / 255, 60 / 255, 120 / 255, 0.35)

    // Text
    readonly property color text: dark ? "#F1F4FB" : "#182033"
    readonly property color muted: dark ? "#7D879F" : "#8A93A8"
    readonly property color secondary: dark ? "#A4ADC2" : "#5B6478"
    readonly property color title: dark ? "#8D97AE" : "#5B6478"
    readonly property color ink: dark ? "#E8ECF6" : "#2C3650"

    // Kinds and states
    readonly property color cobalt: "#2C4BF0"
    readonly property color cobaltText: dark ? "#9FB2FF" : "#2C4BF0"
    readonly property color teal: dark ? "#5FE0CB" : "#0F8F7E"
    readonly property color violet: dark ? "#B3A2FF" : "#6B4FE0"
    readonly property color error: dark ? "#FF8A80" : "#D14343"
    readonly property color gradientTop: "#3D5CFF"
    readonly property color gradientBottom: "#2440E8"
    readonly property color meterEnd: "#6FA8FF"

    // Cards, controls, menus
    readonly property color card: dark ? "#1C2336" : "#FFFFFF"
    readonly property color cardLine: dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.06)
    readonly property color cardShadow: dark ? Qt.rgba(0, 0, 0, 0.8) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.45)
    readonly property color photo: dark ? "#262E44" : "#E8ECF5"
    // Opaque equivalents of white 6 % over the dark glass, so glows never
    // show through the fill (CSS outer shadows are not painted underneath).
    readonly property color pill: dark ? "#22283A" : "#FFFFFF"
    readonly property color pillHover: dark ? "#2A3146" : "#F7F9FF"
    readonly property color secondaryFill: dark ? "#22283A" : "#FFFFFF"
    readonly property color secondaryLine: dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.10)
    readonly property color menu: dark ? "#1F2639" : "#FFFFFF"
    readonly property color menuLine: dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.08)
    readonly property color hoverFill: dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(44 / 255, 75 / 255, 240 / 255, 0.06)
    readonly property color pressFill: dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(44 / 255, 75 / 255, 240 / 255, 0.10)
    readonly property color hairline: dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.08)
    readonly property color track: dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(44 / 255, 75 / 255, 240 / 255, 0.10)
    readonly property color field: dark ? Qt.rgba(1, 1, 1, 0.05) : "#F4F6FB"
    readonly property color scrim: dark ? Qt.rgba(5 / 255, 8 / 255, 16 / 255, 0.55) : Qt.rgba(24 / 255, 32 / 255, 51 / 255, 0.18)
    readonly property color menuShadow: dark ? Qt.rgba(0, 0, 0, 0.6) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.28)
    readonly property color transparent: "transparent"

    function kindColor(kind) {
        return kind === "video" ? teal : (kind === "audio" ? violet
            : (kind === "image" ? cobaltText : (kind === "error" ? error : ink)))
    }
    // Pill outline and glow use the kind's hue; in dark mode the lighter tint.
    function kindLine(kind) {
        var c = Qt.color(kind === "neutral" ? (dark ? "#E8ECF6" : "#1E326E") : kindColor(kind))
        return Qt.rgba(c.r, c.g, c.b, kind === "neutral" ? (dark ? 0.16 : 0.13) : (dark ? 0.27 : 0.19))
    }
    function kindGlow(kind) {
        if (kind === "error")
            return Qt.rgba(209 / 255, 67 / 255, 67 / 255, dark ? 0.6 : 0.4)
        var source = dark
            ? (kind === "video" ? "#14AA96" : (kind === "audio" ? "#785AFF" : (kind === "image" ? "#3D5CFF" : "#000000")))
            : (kind === "video" ? "#0F8F7E" : (kind === "audio" ? "#6B4FE0" : (kind === "image" ? "#2C4BF0" : "#1E326E")))
        var c = Qt.color(source)
        return Qt.rgba(c.r, c.g, c.b, dark ? 0.8 : (kind === "neutral" ? 0.35 : 0.5))
    }
    function kindTint(kind) {
        var c = Qt.color(kindColor(kind))
        return Qt.rgba(c.r, c.g, c.b, dark ? 0.14 : 0.10)
    }

    // Type: SF Pro Rounded when installed. CoreText will not resolve the
    // system's private rounded face by name, so otherwise use the system font.
    readonly property string latinFont: Qt.fontFamilies().indexOf("SF Pro Rounded") >= 0
        ? "SF Pro Rounded"
        : (Qt.platform.os === "osx" || Qt.platform.os === "macos" ? ".AppleSystemUIFont" : "Inter")
    // Qt's CJK fallback drops the requested weight, so Chinese text names
    // PingFang directly. Set from Main.qml.
    property string language: "en"
    readonly property string cjkFont: Qt.fontFamilies().indexOf("PingFang SC") >= 0 ? "PingFang SC" : latinFont
    readonly property string font: language === "zh" ? cjkFont : latinFont

    function fontFor(text) {
        return /[\u3000-\u9fff\uff00-\uffef]/.test(text || "") ? cjkFont : latinFont
    }

    // Shape
    readonly property int radiusPanel: 26
    readonly property int radiusPill: 14
    readonly property int radiusButton: 20
    readonly property int radiusCard: 20
    readonly property int radiusMenu: 14
    readonly property int buttonHeight: 56
    readonly property int pillHeight: 44

    // "rrggbb" without the hash, for tinting provider icons.
    function hex(value) {
        return Qt.color(value).toString().substring(1, 7)
    }
}
