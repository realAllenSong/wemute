import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// A small rounded sheet centred over the window.
Popup {
    id: sheet
    parent: Overlay.overlay
    anchors.centerIn: parent
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }

    Overlay.modal: Rectangle { color: Theme.scrim }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
        NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 200; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: 110 }
    }

    background: Item {
        RectangularShadow {
            anchors.fill: parent
            offset.y: 30
            blur: 60
            spread: -24
            radius: Theme.radiusPanel
            color: Theme.panelShadow
        }
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusPanel
            color: Theme.dark ? "#161C2D" : "#FBFCFF"
            border.width: 1
            border.color: Theme.dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.08)
        }
    }
}
