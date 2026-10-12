import QtQuick
import QtQuick.Layouts
import "."

ColumnLayout {
    id: section
    property string title: ""
    property string description: ""
    spacing: 3
    Layout.fillWidth: true
    Layout.topMargin: 6

    Text {
        text: section.title
        color: Theme.text
        font.family: Theme.uiFont
        font.pixelSize: 13
        font.weight: Font.DemiBold
    }
    Text {
        text: section.description
        visible: text.length > 0
        color: Theme.mutedText
        font.family: Theme.uiFont
        font.pixelSize: 12
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
}
