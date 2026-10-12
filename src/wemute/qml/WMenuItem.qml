import QtQuick
import QtQuick.Controls
import "."

MenuItem {
    id: item
    property string iconName: ""
    property string shortcutText: ""
    property bool destructive: false

    implicitHeight: visible ? 30 : 0
    leftPadding: 10
    rightPadding: 10

    readonly property color ink: !enabled ? Theme.subtleText : (destructive ? Theme.error : Theme.text)

    contentItem: Item {
        implicitWidth: label.implicitWidth + 60
        Image {
            id: glyph
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 15
            height: 15
            sourceSize: Qt.size(15, 15)
            visible: item.checkable ? item.checked : item.iconName.length > 0
            source: !visible ? ""
                : "image://icons/" + (item.checkable ? "check" : item.iconName) + "/"
                    + Theme.hex(item.checkable ? Theme.cobalt : (item.destructive ? Theme.error : Theme.secondaryText))
        }
        Text {
            id: label
            anchors.left: parent.left
            anchors.leftMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            text: item.text
            color: item.ink
            font.family: Theme.uiFont
            font.pixelSize: 13
        }
        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: item.shortcutText
            visible: text.length > 0
            color: Theme.mutedText
            font.family: Theme.uiFont
            font.pixelSize: 12
        }
    }

    indicator: Item { }

    background: Rectangle {
        radius: 6
        color: item.highlighted && item.enabled ? Theme.hoverFill : Theme.transparent
    }
}
