import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// ⌘K: type a few letters in Chinese or English, ↑↓ to choose, ⏎ to run.
Popup {
    id: commandPalette
    property var results: []

    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round(Math.max(56, parent.height * 0.14))
    width: Math.min(560, parent.width - 48)
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    Overlay.modal: Rectangle { color: Theme.dark ? Qt.rgba(5 / 255, 8 / 255, 16 / 255, 0.35) : Qt.rgba(24 / 255, 32 / 255, 51 / 255, 0.08) }

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }
    function openWith(query) {
        field.text = query || ""
        refresh()
        open()
    }
    function refresh() {
        results = actionCenter.search(field.text)
        list.currentIndex = results.length > 0 ? 0 : -1
        list.positionViewAtBeginning()
    }
    function runAt(index) {
        if (index < 0 || index >= results.length)
            return
        var id = results[index].id
        close()
        actionCenter.run(id)
    }
    function shortcutLabel(sequence) {
        if (!sequence)
            return ""
        return sequence.replace("Ctrl+", "⌘").replace("Shift+", "⇧").replace("Backspace", "⌫")
    }

    onOpened: field.forceActiveFocus()
    Connections {
        target: actionCenter
        function onMenuChanged() { if (commandPalette.opened) commandPalette.refresh() }
    }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.reduceMotion ? 0 : 120 }
        NumberAnimation { property: "scale"; from: Theme.reduceMotion ? 1 : 0.98; to: 1; duration: 160; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: Theme.reduceMotion ? 0 : 90 }
    }

    background: Item {
        RectangularShadow {
            anchors.fill: parent
            offset.y: 22
            blur: 50
            spread: -16
            radius: 18
            color: Theme.menuShadow
        }
        Rectangle {
            anchors.fill: parent
            radius: 18
            color: Theme.menu
            border.width: 1
            border.color: Theme.menuLine
        }
    }

    contentItem: Column {
        spacing: 0

        Item {
            width: parent.width
            height: 54
            Image {
                id: searchGlyph
                anchors.left: parent.left
                anchors.leftMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                width: 17
                height: 17
                sourceSize: Qt.size(17, 17)
                source: "image://icons/search/" + Theme.hex(Theme.muted) + "/2.4"
            }
            TextField {
                id: field
                anchors.left: searchGlyph.right
                anchors.leftMargin: 10
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: commandPalette.tr("palette_placeholder")
                placeholderTextColor: Theme.muted
                color: Theme.text
                selectionColor: Theme.kindLine("image")
                selectedTextColor: Theme.text
                font.family: Theme.fontFor(text.length > 0 ? text : placeholderText)
                font.pixelSize: 18
                font.weight: Font.Bold
                background: null
                padding: 0
                Accessible.name: commandPalette.tr("tb_search")
                onTextEdited: commandPalette.refresh()
                Keys.onUpPressed: list.currentIndex = Math.max(0, list.currentIndex - 1)
                Keys.onDownPressed: list.currentIndex = Math.min(commandPalette.results.length - 1, list.currentIndex + 1)
                Keys.onReturnPressed: commandPalette.runAt(list.currentIndex)
                Keys.onEnterPressed: commandPalette.runAt(list.currentIndex)
                Keys.onEscapePressed: commandPalette.close()
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.hairline
        }

        ListView {
            id: list
            width: parent.width
            height: commandPalette.results.length > 0 ? Math.min(contentHeight + 12, 8 * 42 + 12) : 0
            topMargin: 6
            bottomMargin: 6
            clip: true
            model: commandPalette.results
            boundsBehavior: Flickable.StopAtBounds
            highlightMoveDuration: 0
            keyNavigationEnabled: false
            ScrollIndicator.vertical: ScrollIndicator { }
            onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)

            delegate: Item {
                id: row
                required property var modelData
                required property int index
                readonly property bool current: ListView.isCurrentItem
                width: list.width
                height: 42

                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    radius: 10
                    color: row.current ? Theme.kindTint("image") : "transparent"
                }
                Rectangle {
                    id: tile
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    width: 28
                    height: 28
                    radius: 8
                    color: Theme.kindTint(row.modelData.tint)
                    Image {
                        anchors.centerIn: parent
                        width: 15
                        height: 15
                        sourceSize: Qt.size(15, 15)
                        source: "image://icons/" + row.modelData.icon + "/" + Theme.hex(Theme.kindColor(row.modelData.tint)) + "/2.2"
                    }
                }
                Text {
                    anchors.left: tile.right
                    anchors.leftMargin: 12
                    anchors.right: trailing.left
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: row.modelData.label
                    color: row.current ? Theme.cobaltText : Theme.text
                    font.family: Theme.fontFor(text)
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    elide: Text.ElideRight
                }
                Row {
                    id: trailing
                    anchors.right: parent.right
                    anchors.rightMargin: 18
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Tag {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: (row.modelData.tag || "").length > 0
                        text: visible ? commandPalette.tr(row.modelData.tag) : ""
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: (row.modelData.shortcut || "").length > 0
                        text: commandPalette.shortcutLabel(row.modelData.shortcut)
                        color: Theme.muted
                        font.family: Theme.latinFont
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: row.modelData.category
                        color: Theme.muted
                        font.family: Theme.fontFor(text)
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }
                }
                HoverHandler {
                    cursorShape: Qt.PointingHandCursor
                    onHoveredChanged: if (hovered) list.currentIndex = row.index
                }
                TapHandler { onTapped: commandPalette.runAt(row.index) }
                Accessible.role: Accessible.Button
                Accessible.name: row.modelData.label + ", " + row.modelData.category
            }
        }

        Text {
            visible: commandPalette.results.length === 0
            width: parent.width
            height: 64
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: commandPalette.tr("palette_empty")
            color: Theme.muted
            font.family: Theme.font
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.hairline
        }
        Item {
            width: parent.width
            height: 34
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                text: commandPalette.tr("palette_keys")
                color: Theme.muted
                font.family: Theme.font
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }
        }
    }
}
