import QtQuick
import "."

// Sunken track with a raised thumb that slides to the selected segment.
Rectangle {
    id: control
    property var options: []      // [{ "key": "...", "label": "..." }]
    property string current: ""
    property bool stretch: false
    signal activated(string key)

    readonly property int currentIndex: {
        for (var i = 0; i < options.length; i++)
            if (options[i].key === current)
                return i
        return -1
    }

    implicitHeight: 30
    implicitWidth: segments.implicitWidth + 4
    radius: Theme.radiusControl
    color: Theme.sunken

    Rectangle {
        id: thumb
        readonly property Item target: control.currentIndex >= 0 ? repeater.itemAt(control.currentIndex) : null
        visible: target !== null
        x: target ? segments.x + target.x : 0
        y: 2
        width: target ? target.width : 0
        height: control.height - 4
        radius: Theme.radiusControl - 2
        color: Theme.raised
        border.width: Theme.dark ? 1 : 0
        border.color: Theme.border

        Rectangle {
            z: -1
            anchors.fill: parent
            anchors.topMargin: 1
            anchors.bottomMargin: -1
            radius: parent.radius
            color: Theme.shadow
            visible: !Theme.dark
        }

        Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    }

    Row {
        id: segments
        x: 2
        y: 2
        height: control.height - 4
        spacing: 0

        Repeater {
            id: repeater
            model: control.options

            Item {
                required property var modelData
                required property int index
                readonly property bool selected: modelData.key === control.current
                width: control.stretch
                    ? (control.width - 4) / Math.max(1, control.options.length)
                    : Math.max(60, label.implicitWidth + 26)
                height: segments.height

                Text {
                    id: label
                    anchors.centerIn: parent
                    text: parent.modelData.label
                    color: parent.selected ? Theme.text : (hover.hovered ? Theme.text : Theme.secondaryText)
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                    font.weight: parent.selected ? Font.DemiBold : Font.Medium
                }

                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: {
                        if (!parent.selected)
                            control.activated(parent.modelData.key)
                    }
                }
            }
        }
    }
}
