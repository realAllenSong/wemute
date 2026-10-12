import QtQuick
import "."

// Soft tag: a pale fill with text of the same hue.
Rectangle {
    id: tag
    property string text: ""
    property string tone: "neutral"
    property string iconName: ""
    property bool mono: false
    readonly property var tones: Theme.tags[tone] || Theme.tags["neutral"]

    implicitWidth: row.implicitWidth + 14
    implicitHeight: 22
    radius: 6
    color: tones[1]
    border.width: 1
    border.color: tones[2]

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 4

        Image {
            anchors.verticalCenter: parent.verticalCenter
            visible: tag.iconName.length > 0
            width: 12
            height: 12
            sourceSize: Qt.size(12, 12)
            source: visible ? "image://icons/" + tag.iconName + "/" + tag.tones[0].substring(1) : ""
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: tag.text
            color: tag.tones[0]
            font.family: tag.mono ? Theme.monoFont : Theme.uiFont
            font.features: { "tnum": 1 }
            font.pixelSize: tag.mono ? 11 : 12
            font.weight: Font.DemiBold
        }
    }
}
