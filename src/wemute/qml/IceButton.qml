import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// kind: "primary" (cobalt gradient) | "secondary" (white, hairline) | "quiet"
Button {
    id: control
    property string kind: "primary"
    property string trailingIcon: ""
    property int fontSize: kind === "primary" ? 18 : 17
    readonly property bool primary: kind === "primary"
    readonly property color foreground: primary ? "#FFFFFF" : (kind === "quiet" ? Theme.secondary : Theme.ink)

    implicitHeight: Theme.buttonHeight
    implicitWidth: label.implicitWidth + (trailingIcon.length > 0 ? 28 : 0) + (primary ? 60 : 48)
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : 0.5
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }

    HoverHandler { cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }

    contentItem: Item {
        Row {
            anchors.centerIn: parent
            spacing: 10
            Text {
                id: label
                anchors.verticalCenter: parent.verticalCenter
                text: control.text
                color: control.foreground
                font.family: Theme.font
                font.pixelSize: control.fontSize
                font.weight: Font.Bold
            }
            Image {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.trailingIcon.length > 0
                width: 18
                height: 18
                sourceSize: Qt.size(18, 18)
                source: visible ? "image://icons/" + control.trailingIcon + "/" + Theme.hex(control.foreground) + "/2.5" : ""
            }
        }
    }

    background: Item {
        RectangularShadow {
            anchors.fill: parent
            visible: control.primary && control.enabled
            offset.y: 16
            blur: 30
            spread: -12
            radius: Theme.radiusButton
            color: Qt.rgba(44 / 255, 75 / 255, 240 / 255, Theme.dark ? 0.6 : 0.7)
        }
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusButton
            visible: control.primary
            gradient: Gradient {
                GradientStop { position: 0; color: control.down ? "#3352F2" : (control.hovered ? "#4D6AFF" : Theme.gradientTop) }
                GradientStop { position: 1; color: control.down ? "#1E38D0" : (control.hovered ? "#2A47F0" : Theme.gradientBottom) }
            }
            // Inner top highlight.
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0; color: Qt.rgba(1, 1, 1, 0.22) }
                    GradientStop { position: 0.06; color: Qt.rgba(1, 1, 1, 0) }
                }
            }
        }
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusButton
            visible: !control.primary
            color: control.kind === "quiet"
                ? (control.down ? Theme.pressFill : (control.hovered ? Theme.hoverFill : "transparent"))
                : (control.down ? Theme.pillHover : (control.hovered ? Theme.pillHover : Theme.secondaryFill))
            border.width: 1
            border.color: Theme.secondaryLine
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -4
            radius: Theme.radiusButton + 4
            color: "transparent"
            border.width: 2
            border.color: Theme.kindLine("image")
            visible: control.visualFocus
        }
    }
}
