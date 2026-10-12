import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// Outlined select.
ComboBox {
    id: control
    property string leadingIcon: ""     // icon name, e.g. "image"
    property string prefixText: ""
    property string placeholderText: ""
    property bool emphasized: false
    implicitWidth: 180
    implicitHeight: Theme.controlHeight
    hoverEnabled: true
    leftPadding: 0
    rightPadding: 0
    focusPolicy: Qt.TabFocus

    HoverHandler { cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }

    contentItem: Item {
        Image {
            id: currentIcon
            anchors.left: parent.left
            anchors.leftMargin: 11
            anchors.verticalCenter: parent.verticalCenter
            width: 15
            height: 15
            sourceSize: Qt.size(15, 15)
            visible: control.leadingIcon.length > 0
            source: visible ? "image://icons/" + control.leadingIcon + "/" + Theme.hex(Theme.mutedText) : ""
        }
        Text {
            id: prefix
            anchors.left: currentIcon.visible ? currentIcon.right : parent.left
            anchors.leftMargin: currentIcon.visible ? 8 : 12
            anchors.verticalCenter: parent.verticalCenter
            visible: control.prefixText.length > 0 && control.currentIndex >= 0
            text: control.prefixText
            color: Theme.mutedText
            font.family: Theme.uiFont
            font.pixelSize: 13
        }
        Text {
            anchors.left: prefix.visible ? prefix.right : (currentIcon.visible ? currentIcon.right : parent.left)
            anchors.leftMargin: prefix.visible ? 5 : (currentIcon.visible ? 8 : 12)
            anchors.right: parent.right
            anchors.rightMargin: 30
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            text: control.currentIndex >= 0 ? control.currentText : control.placeholderText
            color: !control.enabled
                ? Theme.subtleText
                : (control.currentIndex >= 0 ? Theme.text : Theme.mutedText)
            font.family: Theme.uiFont
            font.pixelSize: 13
            font.weight: control.emphasized ? Font.DemiBold : Font.Medium
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    indicator: Image {
        width: 14
        height: 14
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        sourceSize: Qt.size(14, 14)
        source: "image://icons/chevron-down/" + Theme.hex(Theme.mutedText)
        opacity: control.enabled ? 1 : 0.5
    }

    background: Rectangle {
        color: !control.enabled ? Theme.canvas : (control.hovered ? Theme.surfaceHover : Theme.surface)
        radius: Theme.radiusControl
        border.width: 1
        border.color: control.popup.visible
            ? Theme.borderStrong
            : (control.hovered ? Theme.borderStrong : Theme.border)

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.width: 2
            border.color: Theme.cobaltLine
            visible: control.visualFocus
        }
    }

    popup: Popup {
        y: control.height + 4
        width: Math.max(control.width, 190)
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 380)
        padding: 5

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollIndicator.vertical: ScrollIndicator { }
        }

        background: Rectangle {
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

    delegate: ItemDelegate {
        id: option
        required property int index
        required property var modelData
        width: ListView.view ? ListView.view.width : control.width
        height: 30
        highlighted: control.highlightedIndex === index
        leftPadding: 10
        rightPadding: 10

        contentItem: Item {
            Text {
                anchors.left: parent.left
                anchors.right: check.left
                anchors.verticalCenter: parent.verticalCenter
                text: option.modelData
                color: Theme.text
                font.family: Theme.uiFont
                font.pixelSize: 13
                font.weight: control.currentIndex === option.index ? Font.DemiBold : Font.Normal
                elide: Text.ElideRight
            }
            Image {
                id: check
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 14
                height: 14
                sourceSize: Qt.size(14, 14)
                visible: control.currentIndex === option.index
                source: visible ? "image://icons/check/" + Theme.hex(Theme.cobalt) : ""
            }
        }

        background: Rectangle {
            radius: 6
            color: option.highlighted ? Theme.hoverFill : Theme.transparent
        }
    }
}
