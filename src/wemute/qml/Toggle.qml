import QtQuick
import QtQuick.Controls
import "."

// Switch: cobalt when on.
AbstractButton {
    id: control
    checkable: true
    implicitWidth: 36
    implicitHeight: 20
    padding: 0
    focusPolicy: Qt.TabFocus

    HoverHandler { cursorShape: Qt.PointingHandCursor }

    background: Rectangle {
        radius: height / 2
        color: control.checked ? Theme.cobalt : Theme.sunken
        Behavior on color { ColorAnimation { duration: 110 } }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: height / 2
            color: "transparent"
            border.width: 1.5
            border.color: Theme.cobaltLine
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
            border.width: control.checked ? 0 : 1
            border.color: Theme.border
            Behavior on x { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
        }
    }
}
