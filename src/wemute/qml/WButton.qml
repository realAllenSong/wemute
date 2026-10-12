import QtQuick
import QtQuick.Controls
import "."

// Compact button for sheets. kind: "primary" | "secondary" | "ghost"
Button {
    id: control
    property string kind: "secondary"
    property string iconName: ""
    property int iconSize: 15
    property int fontSize: 13

    readonly property bool solid: kind === "primary"
    readonly property color foreground: solid ? "#FFFFFF" : (kind === "ghost" && !hovered ? Theme.secondary : Theme.ink)

    implicitHeight: 34
    implicitWidth: Math.max(implicitHeight, contentRow.implicitWidth + (text.length > 0 ? 28 : 14))
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : 0.45

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
                source: visible ? "image://icons/" + control.iconName + "/" + Theme.hex(control.foreground) + "/2" : ""
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.text.length > 0
                text: control.text
                color: control.foreground
                font.family: Theme.font
                font.pixelSize: control.fontSize
                font.weight: Font.Bold
            }
        }
    }

    background: Rectangle {
        radius: 12
        color: control.kind === "ghost"
            ? (control.down ? Theme.pressFill : (control.hovered ? Theme.hoverFill : "transparent"))
            : (control.kind === "secondary" ? (control.hovered ? Theme.pillHover : Theme.secondaryFill) : "transparent")
        border.width: control.kind === "secondary" ? 1 : 0
        border.color: Theme.secondaryLine
        gradient: control.solid ? solidGradient : null

        Gradient {
            id: solidGradient
            GradientStop { position: 0; color: control.hovered ? "#4D6AFF" : Theme.gradientTop }
            GradientStop { position: 1; color: control.hovered ? "#2A47F0" : Theme.gradientBottom }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.width: 2
            border.color: Theme.kindLine("image")
            visible: control.visualFocus
        }
    }
}
