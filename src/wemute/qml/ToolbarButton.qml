import QtQuick
import QtQuick.Controls
import "."

// A small card-coloured button for the title bar: 「工具 ▾」「⌘K」「设置」.
Button {
    id: control
    property string iconName: ""
    property bool chevron: false
    property bool quiet: false   // muted text, for the ⌘K hint
    property bool open: false

    readonly property color foreground: quiet ? Theme.secondary : Theme.ink

    implicitHeight: 28
    implicitWidth: contentRow.implicitWidth + 20
    hoverEnabled: true
    focusPolicy: Qt.TabFocus

    HoverHandler { cursorShape: Qt.PointingHandCursor }

    contentItem: Item {
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 5

            Image {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.iconName.length > 0
                width: 13
                height: 13
                sourceSize: Qt.size(13, 13)
                source: visible ? "image://icons/" + control.iconName + "/" + Theme.hex(control.foreground) + "/2.3" : ""
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.text.length > 0
                text: control.text
                color: control.foreground
                font.family: Theme.fontFor(text)
                font.pixelSize: 12
                font.weight: Font.Bold
            }
            Image {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.chevron
                width: 11
                height: 11
                sourceSize: Qt.size(11, 11)
                source: visible ? "image://icons/chevron-down/" + Theme.hex(control.foreground) + "/2.8" : ""
            }
        }
    }

    background: Rectangle {
        radius: 9
        color: control.down || control.open ? Theme.pillHover : (control.hovered ? Theme.pillHover : Theme.card)
        border.width: 1
        border.color: control.open ? Theme.kindLine("image") : Theme.secondaryLine
        opacity: Theme.dark ? 0.94 : 0.9

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
