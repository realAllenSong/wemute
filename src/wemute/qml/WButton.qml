import QtQuick
import QtQuick.Controls
import "."

Button {
    id: control
    property bool primary: false
    property bool quiet: false

    implicitHeight: Theme.controlHeight
    implicitWidth: primary ? 174 : Math.max(118, contentItem.implicitWidth + 30)
    hoverEnabled: true

    contentItem: Text {
        text: control.text
        color: control.enabled
            ? (control.primary ? "white" : Theme.text)
            : Theme.tertiaryText
        font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
        font.pixelSize: control.primary ? 17 : 15
        font.weight: control.primary ? Font.Medium : Font.Normal
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radius
        color: {
            if (control.primary)
                return control.down ? "#1767DE" : (control.hovered ? Theme.accentHover : Theme.accent)
            if (control.quiet)
                return control.hovered ? Theme.surfaceHover : Theme.transparent
            return control.hovered ? Theme.surfaceHover : Theme.surface
        }
        border.width: control.primary || control.quiet ? 0 : 1
        border.color: Theme.border
        opacity: control.enabled ? 1 : 0.55
    }
}
