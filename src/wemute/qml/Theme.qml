pragma Singleton
import QtQuick

// "Porcelain & Cobalt" — drawn from the app icon: cool porcelain sheets on
// graphite, joined by one electric cobalt seam. Cobalt is the only accent and
// always means "transformation": progress, the primary action, focus.
// Follows the system appearance.
QtObject {
    id: theme
    readonly property bool dark: Application.styleHints.colorScheme === Qt.ColorScheme.Dark

    // Surfaces
    readonly property color canvas: dark ? "#111317" : "#F3F4F6"
    readonly property color surface: dark ? "#1A1D22" : "#FFFFFF"
    readonly property color surfaceHover: dark ? "#1F2329" : "#FAFBFC"
    readonly property color selected: dark ? "#222833" : "#F1F4FF"
    readonly property color sunken: dark ? "#0D0F12" : "#E9EBEF"
    readonly property color raised: dark ? "#262A31" : "#FFFFFF"
    readonly property color toolbar: dark ? "#15171B" : "#F8F9FA"

    // Graphite text
    readonly property color text: dark ? "#ECEEF1" : "#15181D"
    readonly property color secondaryText: dark ? "#A6ACB6" : "#59606B"
    readonly property color mutedText: dark ? "#7C838E" : "#878E99"
    readonly property color subtleText: dark ? "#545A63" : "#B3B8C0"

    // Hairlines and interaction fills
    readonly property color hairline: dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.07)
    readonly property color border: dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.11)
    readonly property color borderStrong: dark ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.22)
    // Opaque card outline so stacked rows never double their dividers.
    readonly property color cardOutline: dark ? "#2A2E35" : "#E2E4E8"
    readonly property color hoverFill: dark ? Qt.rgba(1, 1, 1, 0.05) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.045)
    readonly property color pressFill: dark ? Qt.rgba(1, 1, 1, 0.09) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.08)
    readonly property color shadow: dark ? Qt.rgba(0, 0, 0, 0.45) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.10)
    readonly property color scrim: dark ? Qt.rgba(0, 0, 0, 0.45) : Qt.rgba(20 / 255, 23 / 255, 28 / 255, 0.18)

    // Cobalt seam
    readonly property color cobalt: dark ? "#5672FF" : "#2C4BF0"
    readonly property color cobaltHover: dark ? "#6B84FF" : "#2340D6"
    readonly property color cobaltPressed: dark ? "#4A63E6" : "#1C35BD"
    readonly property color cobaltSoft: dark ? Qt.rgba(86 / 255, 114 / 255, 1, 0.16) : Qt.rgba(44 / 255, 75 / 255, 240 / 255, 0.09)
    readonly property color cobaltLine: dark ? Qt.rgba(86 / 255, 114 / 255, 1, 0.45) : Qt.rgba(44 / 255, 75 / 255, 240 / 255, 0.35)

    readonly property color success: dark ? "#3FB37F" : "#17845A"
    readonly property color error: dark ? "#F0675C" : "#C8372D"
    readonly property color warning: dark ? "#E0A43A" : "#A86A0C"
    readonly property color transparent: "transparent"

    // Soft tags: text, fill, outline
    readonly property var tags: dark ? ({
        "neutral": ["#B7BDC6", "#23272D", "#2E333A"],
        "cobalt": ["#9DB0FF", "#1D2541", "#2C3866"],
        "green": ["#7FD3AA", "#16291F", "#21402F"],
        "red": ["#FF9C93", "#341A19", "#4D2422"],
        "amber": ["#F2C779", "#30260F", "#4A3A17"]
    }) : ({
        "neutral": ["#59606B", "#F1F2F4", "#E3E5E9"],
        "cobalt": ["#2340D6", "#EEF1FF", "#D6DDFE"],
        "green": ["#146C4A", "#EAF6F0", "#CDE9DB"],
        "red": ["#A92E25", "#FDEEEC", "#F7D2CE"],
        "amber": ["#8A5A0B", "#FCF4E3", "#F1DFB7"]
    })

    // Type — one sans family; figures use tabular numerals ("tnum") so sizes
    // and percentages line up without switching to a dated monospace.
    readonly property string uiFont: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
    readonly property string monoFont: uiFont

    // Shape and rhythm
    readonly property int radiusControl: 9
    readonly property int radiusCard: 14
    readonly property int controlHeight: 32
    readonly property int contentMaxWidth: 1000
    readonly property int pageMargin: 28
    readonly property int toolbarHeight: 52

    // "#rrggbb" without the hash, for tinting provider icons.
    function hex(value) {
        return Qt.color(value).toString().substring(1, 7)
    }
}
