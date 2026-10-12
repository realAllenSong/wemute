pragma Singleton
import QtQuick

QtObject {
    readonly property color window: "#16191C"
    readonly property color windowDeep: "#131619"
    readonly property color surface: "#1D2125"
    readonly property color surfaceHover: "#22272C"
    readonly property color surfaceSelected: "#24292E"
    readonly property color border: "#343A40"
    readonly property color divider: "#2C3136"
    readonly property color text: "#F1F2F3"
    readonly property color secondaryText: "#A5ABB2"
    readonly property color tertiaryText: "#747B83"
    readonly property color accent: "#287BFF"
    readonly property color accentHover: "#3B89FF"
    readonly property color error: "#FF6B6B"
    readonly property color success: "#3DD68C"
    readonly property color transparent: "transparent"

    readonly property int pageMargin: 40
    readonly property int rowHeight: 104
    readonly property int headerHeight: 50
    readonly property int controlHeight: 52
    readonly property int radius: 10
}
