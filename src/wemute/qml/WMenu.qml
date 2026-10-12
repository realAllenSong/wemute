import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

Menu {
    id: menu
    padding: 5
    implicitWidth: 240
    delegate: WMenuItem { }

    background: Rectangle {
        implicitWidth: 240
        color: Theme.raised
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.shadow
            shadowBlur: 0.9
            shadowVerticalOffset: 6
            shadowOpacity: Theme.dark ? 0.9 : 0.55
        }
        radius: 11
        border.width: 1
        border.color: Theme.border

    }
}
