import QtQuick
import QtQuick.Controls
import "."

// Switch: cobalt gradient when on.
AbstractButton {
    id: control
    checkable: true
    implicitWidth: 44
    implicitHeight: 26
    padding: 0
    focusPolicy: Qt.TabFocus

    HoverHandler { cursorShape: Qt.PointingHandCursor }

    background: Rectangle {
        radius: height / 2
        color: Theme.track
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            opacity: control.checked ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 120 } }
            gradient: Gradient {
                GradientStop { position: 0; color: Theme.gradientTop }
                GradientStop { position: 1; color: Theme.gradientBottom }
            }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: height / 2
            color: "transparent"
            border.width: 2
            border.color: Theme.kindLine("image")
            visible: control.visualFocus
        }
    }

    contentItem: Item {
        Rectangle {
            width: control.height - 6
            height: width
            radius: width / 2
            y: 3
            x: control.checked ? control.width - width - 3 : 3
            color: "#FFFFFF"
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }
}
