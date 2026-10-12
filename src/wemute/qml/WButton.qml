import QtQuick
import QtQuick.Controls
import "."

// kind: "primary" (cobalt) | "secondary" (outlined surface) | "ghost" | "danger"
Button {
    id: control
    property string kind: primary ? "primary" : (quiet ? "ghost" : "secondary")
    property bool primary: false
    property bool quiet: false
    property string iconName: ""
    property int iconSize: 15
    property int fontSize: 13

    readonly property bool solid: kind === "primary" || kind === "danger"
    readonly property color foreground: !enabled
        ? Theme.subtleText
        : (solid ? "#FFFFFF" : (kind === "ghost" && !hovered ? Theme.secondaryText : Theme.text))

    implicitHeight: Theme.controlHeight
    implicitWidth: Math.max(implicitHeight, contentRow.implicitWidth + (text.length > 0 ? 26 : 14))
    hoverEnabled: true
    focusPolicy: Qt.TabFocus

    HoverHandler { cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }

    contentItem: Item {
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 6

            Image {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.iconName.length > 0
                width: control.iconSize
                height: control.iconSize
                sourceSize: Qt.size(control.iconSize, control.iconSize)
                source: visible ? "image://icons/" + control.iconName + "/" + Theme.hex(control.foreground) : ""
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.text.length > 0
                text: control.text
                color: control.foreground
                font.family: Theme.uiFont
                font.pixelSize: control.fontSize
                font.weight: control.solid ? Font.DemiBold : Font.Medium
            }
        }
    }

    background: Rectangle {
        radius: Theme.radiusControl
        color: {
            if (!control.enabled)
                return control.solid ? Theme.sunken : Theme.transparent
            if (control.kind === "primary")
                return control.down ? Theme.cobaltPressed : (control.hovered ? Theme.cobaltHover : Theme.cobalt)
            if (control.kind === "danger")
                return control.down ? Qt.darker(Theme.error, 1.2) : (control.hovered ? Qt.darker(Theme.error, 1.08) : Theme.error)
            if (control.kind === "ghost")
                return control.down ? Theme.pressFill : (control.hovered ? Theme.hoverFill : Theme.transparent)
            return control.down ? Theme.sunken : (control.hovered ? Theme.surfaceHover : Theme.surface)
        }
        border.width: control.kind === "secondary" ? 1 : 0
        border.color: control.hovered && control.enabled ? Theme.borderStrong : Theme.border

        // Primary actions carry a faint cobalt glow, echoing the icon's seam.
        Rectangle {
            z: -1
            anchors.fill: parent
            anchors.topMargin: 2
            anchors.bottomMargin: -3
            radius: parent.radius + 2
            color: Theme.cobaltSoft
            visible: control.kind === "primary" && control.enabled
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.width: 2
            border.color: Theme.cobaltLine
            visible: control.visualFocus
        }
    }
}
