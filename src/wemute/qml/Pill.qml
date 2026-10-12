import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// A word in the sentence that can be clicked: white rounded button, tinted
// outline and glow, bold text in the kind's colour, small chevron.
AbstractButton {
    id: pill
    property string kind: "image"       // image | video | audio | neutral
    property int fontSize: 30
    property bool chevron: true
    property bool open: false
    readonly property color tone: Theme.kindColor(kind)

    implicitHeight: Theme.pillHeight
    implicitWidth: row.implicitWidth + 32
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : 0.62
    scale: down ? 0.96 : 1
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }

    HoverHandler { cursorShape: pill.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }

    background: Item {
        RectangularShadow {
            anchors.fill: parent
            offset.y: Theme.dark ? 8 : 6
            blur: Theme.dark ? 18 : 14
            spread: Theme.dark ? -10 : -8
            radius: Theme.radiusPill
            color: Theme.kindGlow(pill.kind)
            visible: pill.enabled
        }
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusPill
            color: pill.hovered || pill.open ? Theme.pillHover : Theme.pill
            border.width: 1
            border.color: Theme.kindLine(pill.kind)
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -4
            radius: Theme.radiusPill + 4
            color: "transparent"
            border.width: 2
            border.color: Theme.kindLine("image")
            visible: pill.visualFocus
        }
    }

    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 9
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: pill.text
                color: pill.tone
                font.family: Theme.fontFor(pill.text)
                font.pixelSize: pill.fontSize
                font.weight: Font.Bold
                font.features: { "tnum": 1 }
            }
            Image {
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: 1
                visible: pill.chevron
                width: Math.round(pill.fontSize * 0.5)
                height: width
                sourceSize: Qt.size(width, height)
                source: "image://icons/chevron-down/" + Theme.hex(pill.tone) + "/3"
                opacity: 0.65
            }
        }
    }
}
