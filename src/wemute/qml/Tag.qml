import QtQuick
import "."

// Small tinted label. tone: "neutral" | "cobalt" | "teal" | "error"
Rectangle {
    id: tag
    property string text: ""
    property string tone: "neutral"
    readonly property color ink: tone === "cobalt" ? Theme.cobaltText
        : (tone === "teal" ? Theme.teal : (tone === "error" ? Theme.error : Theme.secondary))

    implicitWidth: label.implicitWidth + 16
    implicitHeight: 22
    radius: 8
    color: Qt.rgba(ink.r, ink.g, ink.b, Theme.dark ? 0.14 : 0.09)

    Text {
        id: label
        anchors.centerIn: parent
        text: tag.text
        color: tag.ink
        font.family: Theme.font
        font.pixelSize: 11
        font.weight: Font.Bold
        font.features: { "tnum": 1 }
    }
}
