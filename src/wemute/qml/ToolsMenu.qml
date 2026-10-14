import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// 「工具 ▾」: every conversion and tool, grouped like the menu bar's 工具 menu.
// Rows come from actionCenter.menu: { type: header | action | menu }.
Menu {
    id: root
    property var rows: actionCenter.menu
    signal ran(string actionId)

    popupType: Popup.Item
    width: 300
    // Taller than the window would push the menu up over its button; scroll instead.
    property real maxHeight: 0
    contentItem: ListView {
        implicitHeight: root.maxHeight > 0 ? Math.min(contentHeight, root.maxHeight) : contentHeight
        model: root.contentModel
        interactive: contentHeight > height
        clip: true
        currentIndex: root.currentIndex
        ScrollIndicator.vertical: ScrollIndicator { }
    }
    topPadding: 6
    bottomPadding: 6
    leftPadding: 6
    rightPadding: 6
    margins: 10
    delegate: ToolRow { }
    background: MenuPanel { }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.reduceMotion ? 0 : 110 }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: Theme.reduceMotion ? 0 : 80 }
    }

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }

    function clear(menu) {
        while (menu.count > 0) {
            var sub = menu.menuAt(0)
            if (sub) {
                // The row that opens a submenu belongs to the Menu; only the
                // submenu itself was created here.
                clear(sub)
                menu.takeMenu(0)
                sub.destroy()
            } else {
                menu.takeItem(0).destroy()
            }
        }
    }
    function fill(menu, list) {
        for (var i = 0; i < list.length; i++) {
            var row = list[i]
            if (row.type === "header") {
                if (menu.count > 0)
                    menu.addItem(separatorComponent.createObject(menu.contentItem))
                menu.addItem(headerComponent.createObject(menu.contentItem, { "text": row.label }))
            } else if (row.type === "menu") {
                var sub = subMenuComponent.createObject(menu, { "title": row.label })
                fill(sub, row.children)
                menu.addMenu(sub)
            } else {
                menu.addItem(actionComponent.createObject(menu.contentItem, {
                    "text": row.label,
                    "actionId": row.id,
                    "shortcutText": root.shortcutLabel(row.shortcut),
                    "tag": row.tag || ""
                }))
            }
        }
    }
    function rebuild() {
        clear(root)
        fill(root, rows)
    }
    function shortcutLabel(sequence) {
        if (!sequence)
            return ""
        return sequence.replace("Ctrl+", "⌘").replace("Shift+", "⇧").replace("Backspace", "⌫")
    }

    // Never rebuild while open: destroying rows the view is still laying out
    // crashed the app (heap corruption in polishItems). Rebuild on close.
    property bool dirty: false
    onRowsChanged: {
        if (visible)
            dirty = true
        else
            Qt.callLater(rebuild)
    }
    onClosed: {
        if (dirty) {
            dirty = false
            Qt.callLater(rebuild)
        }
    }
    Component.onCompleted: Qt.callLater(rebuild)

    component MenuPanel: Item {
        implicitWidth: 300
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

    // Plain rows and the rows that open a submenu.
    component ToolRow: MenuItem {
        id: item
        property string actionId: ""
        property string shortcutText: ""
        property string tag: ""
        implicitWidth: 288
        implicitHeight: 30
        leftPadding: 10
        rightPadding: 10
        hoverEnabled: true
        arrow: null
        indicator: null

        contentItem: Item {
            Text {
                anchors.left: parent.left
                anchors.right: trailing.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: item.text
                color: item.highlighted ? Theme.cobaltText : Theme.text
                font.family: Theme.fontFor(text)
                font.pixelSize: 13
                font.weight: item.highlighted ? Font.Bold : Font.DemiBold
                elide: Text.ElideRight
            }
            Row {
                id: trailing
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                Tag {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: item.tag.length > 0
                    text: visible ? root.tr(item.tag) : ""
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: item.shortcutText.length > 0
                    text: item.shortcutText
                    color: Theme.muted
                    font.family: Theme.latinFont
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: item.subMenu !== null
                    width: 12
                    height: 12
                    sourceSize: Qt.size(12, 12)
                    source: visible ? "image://icons/chevron-right/"
                        + Theme.hex(item.highlighted ? Theme.cobaltText : Theme.muted) + "/2.6" : ""
                }
            }
        }
        background: Rectangle {
            radius: 8
            color: item.highlighted ? Theme.kindTint("image") : "transparent"
        }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        onTriggered: {
            if (actionId.length > 0) {
                actionCenter.run(actionId)
                root.ran(actionId)
            }
        }
    }

    Component {
        id: actionComponent
        ToolRow { }
    }

    Component {
        id: headerComponent
        MenuItem {
            id: header
            enabled: false
            implicitWidth: 288
            implicitHeight: 24
            leftPadding: 10
            arrow: null
            indicator: null
            background: null
            contentItem: Text {
                text: header.text
                verticalAlignment: Text.AlignBottom
                bottomPadding: 3
                color: Theme.muted
                font.family: Theme.fontFor(text)
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 0.5
                font.capitalization: Font.AllUppercase
            }
        }
    }

    Component {
        id: separatorComponent
        MenuSeparator {
            implicitWidth: 288
            topPadding: 4
            bottomPadding: 2
            contentItem: Rectangle {
                implicitHeight: 1
                color: Theme.hairline
            }
        }
    }

    Component {
        id: subMenuComponent
        Menu {
            popupType: Popup.Item
            width: 260
            topPadding: 6
            bottomPadding: 6
            leftPadding: 6
            rightPadding: 6
            overlap: 4
            delegate: ToolRow { implicitWidth: 248 }
            background: MenuPanel { implicitWidth: 260 }
        }
    }
}
