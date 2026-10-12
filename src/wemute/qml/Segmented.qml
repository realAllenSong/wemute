import QtQuick
import QtQuick.Effects
import "."

// Soft track with a white thumb that slides to the selected segment.
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

    implicitHeight: 36
    implicitWidth: segments.implicitWidth + 6
    radius: 12
    color: Theme.track

    RectangularShadow {
        anchors.fill: thumb
        visible: thumb.visible
        offset.y: 3
        blur: 8
        spread: -3
        radius: thumb.radius
        color: Theme.cardShadow
    }

    Rectangle {
        id: thumb
        // itemAt() is not reactive; repeater.count re-evaluates it once delegates exist.
        readonly property Item target: control.currentIndex >= 0 && control.currentIndex < repeater.count
            ? repeater.itemAt(control.currentIndex) : null
        visible: target !== null
        x: target ? segments.x + target.x : 0
        y: 3
        width: target ? target.width : 0
        height: control.height - 6
        radius: 9
        color: Theme.dark ? "#2C3550" : "#FFFFFF"
        border.width: Theme.dark ? 0 : 1
        border.color: Theme.cardLine
        Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    }

    Row {
        id: segments
        x: 3
        y: 3
        height: control.height - 6

        Repeater {
            id: repeater
            model: control.options

            Item {
                required property var modelData
                required property int index
                readonly property bool selected: modelData.key === control.current
                width: control.stretch
                    ? (control.width - 6) / Math.max(1, control.options.length)
                    : Math.max(56, label.implicitWidth + 28)
                height: segments.height

                Text {
                    id: label
                    anchors.centerIn: parent
                    text: parent.modelData.label
                    color: parent.selected ? Theme.text : (hover.hovered ? Theme.text : Theme.secondary)
                    font.family: Theme.font
                    font.pixelSize: 13
                    font.weight: parent.selected ? Font.Bold : Font.DemiBold
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
