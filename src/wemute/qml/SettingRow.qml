import QtQuick
import QtQuick.Layouts
import "."

// Label + description on the left, a control on the right.
Item {
    id: row
    property string title: ""
    property string description: ""
    property bool showDivider: true
    default property alias control: slot.data

    Layout.fillWidth: true
    implicitHeight: Math.max(54, labels.implicitHeight + 26)

    ColumnLayout {
        id: labels
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.right: slot.left
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3

        Text {
            text: row.title
            color: Theme.text
            font.family: Theme.uiFont
            font.pixelSize: 13
            font.weight: Font.Medium
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        Text {
            text: row.description
            visible: text.length > 0
            color: Theme.mutedText
            font.family: Theme.uiFont
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    Item {
        id: slot
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        width: childrenRect.width
        height: childrenRect.height
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.hairline
        visible: row.showDivider
    }
}
