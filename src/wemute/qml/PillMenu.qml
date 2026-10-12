import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// Rounded popup anchored below a pill. entries: [{ key, label, checked,
// separator, icon }]; a separator entry draws a hairline.
Popup {
    id: menu
    property var entries: []
    property int menuWidth: 248
    signal chosen(string key)

    y: parent ? parent.height + 8 : 0
    width: menuWidth
    padding: 6
    margins: 14
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    transformOrigin: Item.Top

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 }
        NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 160; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: 90 }
    }

    background: Item {
        RectangularShadow {
            anchors.fill: parent
            offset.y: 14
            blur: 34
            spread: -10
            radius: Theme.radiusMenu
            color: Theme.menuShadow
        }
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusMenu
            color: Theme.menu
            border.width: 1
            border.color: Theme.menuLine
        }
    }

    contentItem: ListView {
        id: list
        implicitHeight: Math.min(contentHeight, 420)
        clip: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        model: menu.entries
        ScrollIndicator.vertical: ScrollIndicator { }

        delegate: Item {
            id: entry
            required property var modelData
            readonly property bool separator: modelData.separator === true
            width: list.width
            height: separator ? 11 : 36

            Rectangle {
                visible: entry.separator
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                height: 1
                color: Theme.hairline
            }

            Rectangle {
                visible: !entry.separator
                anchors.fill: parent
                radius: 9
                color: tap.pressed ? Theme.pressFill : (hover.hovered ? Theme.hoverFill : "transparent")
            }

            Image {
                id: glyph
                visible: !entry.separator && (entry.modelData.icon || "").length > 0
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 16
                height: 16
                sourceSize: Qt.size(16, 16)
                source: visible ? "image://icons/" + entry.modelData.icon + "/" + Theme.hex(Theme.secondary) : ""
            }

            Text {
                visible: !entry.separator
                anchors.left: glyph.visible ? glyph.right : parent.left
                anchors.leftMargin: glyph.visible ? 9 : 12
                anchors.right: check.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: entry.modelData.label || ""
                color: Theme.text
                font.family: Theme.fontFor(text)
                font.pixelSize: 14
                font.weight: entry.modelData.checked ? Font.Bold : Font.DemiBold
                elide: Text.ElideRight
            }

            Image {
                id: check
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 16
                height: 16
                sourceSize: Qt.size(16, 16)
                visible: !entry.separator && entry.modelData.checked === true
                source: visible ? "image://icons/check/" + Theme.hex(Theme.cobaltText) + "/2.5" : ""
            }

            HoverHandler {
                id: hover
                enabled: !entry.separator
                cursorShape: Qt.PointingHandCursor
            }
            TapHandler {
                id: tap
                enabled: !entry.separator
                onTapped: {
                    var key = entry.modelData.key
                    menu.close()
                    menu.chosen(key)
                }
            }
        }
    }
}
