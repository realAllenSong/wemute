import QtQuick
import QtQuick.Controls
import "."

ComboBox {
    id: control
    property url leadingIcon
    property string prefixText: ""
    property string placeholderText: ""
    readonly property bool hasLeadingIcon: leadingIcon.toString().length > 0
    implicitWidth: 226
    implicitHeight: Theme.controlHeight
    hoverEnabled: true
    leftPadding: 0
    rightPadding: 0

    contentItem: Item {
        Image {
            id: currentIcon
            anchors.left: parent.left
            anchors.leftMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            width: 20
            height: 20
            source: control.leadingIcon
            sourceSize: Qt.size(20, 20)
            opacity: 0.9
            visible: control.hasLeadingIcon
        }
        Text {
            anchors.left: control.hasLeadingIcon ? currentIcon.right : parent.left
            anchors.leftMargin: control.hasLeadingIcon ? 12 : 16
            anchors.right: parent.right
            anchors.rightMargin: 42
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            text: control.currentIndex >= 0
                ? control.prefixText + control.currentText
                : control.placeholderText
            color: Theme.text
            font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
            font.pixelSize: 16
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    indicator: Image {
        width: 14
        height: 14
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        source: "image://icons/arrow-right"
        rotation: 90
        opacity: 0.72
        sourceSize: Qt.size(14, 14)
    }

    background: Rectangle {
        color: control.hovered ? Theme.surfaceHover : Theme.surface
        radius: Theme.radius
        border.width: 1
        border.color: control.activeFocus ? Theme.accent : Theme.border
    }

    popup: Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 360)
        padding: 6

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator { }
        }

        background: Rectangle {
            color: "#24282D"
            border.width: 1
            border.color: Theme.border
            radius: Theme.radius
        }
    }

    delegate: ItemDelegate {
        width: control.width - 12
        height: 42
        highlighted: control.highlightedIndex === index

        contentItem: Row {
            spacing: 12
            Image {
                width: control.hasLeadingIcon ? 18 : 0
                height: 18
                source: control.leadingIcon
                sourceSize: Qt.size(18, 18)
                opacity: 0.86
                visible: control.hasLeadingIcon
            }
            Text {
                text: modelData
                color: Theme.text
                font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                font.pixelSize: 15
                verticalAlignment: Text.AlignVCenter
            }
        }

        background: Rectangle {
            radius: 7
            color: parent.highlighted ? Theme.surfaceSelected : Theme.transparent
        }
    }
}
