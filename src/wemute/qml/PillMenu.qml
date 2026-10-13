import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// Rounded popup anchored below a pill. entries: [{ key, label, checked,
// separator, header, columnBreak, icon, variants, grid }]:
// - separator draws a hairline and header titles a section;
// - columnBreak starts a second column, for menus with several sections;
// - variants show as chips after the label ("智能裁剪  1:1 4:5 16:9 9:16"),
//   and tapping the row picks the checked or first one;
// - grid lays its choices out as wrapping chips ("WebP JPEG PNG …").
Popup {
    id: menu
    property var entries: []
    property int menuWidth: 248
    signal chosen(string key)

    readonly property var columns: {
        var result = [[]]
        for (var i = 0; i < entries.length; i++) {
            if (entries[i].columnBreak === true)
                result.push([])
            else
                result[result.length - 1].push(entries[i])
        }
        return result
    }
    readonly property bool hasVariants: {
        for (var i = 0; i < entries.length; i++)
            if ((entries[i].variants && entries[i].variants.length > 0) || entries[i].grid)
                return true
        return false
    }
    readonly property int columnWidth: hasVariants ? Math.max(menuWidth, 300) : menuWidth

    y: parent ? parent.height + 8 : 0
    width: columns.length * columnWidth + (columns.length - 1) * 10 + leftPadding + rightPadding
    padding: 6
    margins: 14
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    transformOrigin: Item.Top

    function pick(key) {
        menu.close()
        menu.chosen(key)
    }

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

    contentItem: Flickable {
        id: flick
        implicitHeight: Math.min(columnsRow.implicitHeight, 600)
        contentWidth: width
        contentHeight: columnsRow.implicitHeight
        clip: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        ScrollIndicator.vertical: ScrollIndicator { }

        Repeater {
            // Hairlines between the columns.
            model: menu.columns.length - 1
            Rectangle {
                required property int index
                x: (index + 1) * (menu.columnWidth + columnsRow.spacing) - columnsRow.spacing / 2
                y: 6
                width: 1
                height: columnsRow.implicitHeight - 12
                color: Theme.hairline
            }
        }

        Row {
            id: columnsRow
            spacing: 10
            Repeater {
                model: menu.columns
                Column {
                    id: column
                    required property var modelData
                    width: menu.columnWidth

                    Repeater {
                        model: column.modelData
                        delegate: MenuRow { }
                    }
                }
            }
        }
    }

    component Chip: Rectangle {
        id: chip
        property var choice
        property string context: ""
        width: Math.max(36, chipText.implicitWidth + 16)
        height: 26
        radius: 8
        color: choice.checked ? Theme.cobaltText : (chipHover.hovered ? Theme.pressFill : Theme.hoverFill)
        Text {
            id: chipText
            anchors.centerIn: parent
            text: chip.choice.label
            color: chip.choice.checked ? (Theme.dark ? "#10131C" : "#FFFFFF") : Theme.text
            font.family: Theme.fontFor(text)
            font.pixelSize: 12
            font.weight: Font.Bold
            font.features: { "tnum": 1 }
        }
        HoverHandler { id: chipHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: menu.pick(chip.choice.key) }
        Accessible.role: Accessible.Button
        Accessible.name: (chip.context.length > 0 ? chip.context + " " : "") + chip.choice.label
    }

    component MenuRow: Item {
        id: entry
        required property var modelData
        required property int index
        readonly property bool separator: modelData.separator === true
        readonly property bool header: (modelData.header || "").length > 0
        readonly property bool grid: modelData.grid !== undefined
        readonly property bool plain: !separator && !header && !grid
        readonly property var variants: modelData.variants || []
        width: menu.columnWidth
        height: separator ? 11 : (header ? (index === 0 ? 26 : 34) : (grid ? gridFlow.implicitHeight + 8 : 36))

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

        Text {
            visible: entry.header
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 5
            text: entry.modelData.header || ""
            color: Theme.muted
            font.family: Theme.fontFor(text)
            font.pixelSize: 12
            font.weight: Font.Bold
            font.letterSpacing: 0.4
        }

        Flow {
            id: gridFlow
            visible: entry.grid
            x: 10
            y: 4
            width: parent.width - 20
            spacing: 6
            Repeater {
                model: entry.grid ? entry.modelData.grid : []
                Chip { required property var modelData; choice: modelData }
            }
        }

        Rectangle {
            visible: entry.plain
            anchors.fill: parent
            radius: 9
            color: tap.pressed ? Theme.pressFill : (hover.hovered ? Theme.hoverFill : "transparent")
        }

        Image {
            id: glyph
            visible: entry.plain && (entry.modelData.icon || "").length > 0
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 16
            height: 16
            sourceSize: Qt.size(16, 16)
            source: visible ? "image://icons/" + entry.modelData.icon + "/" + Theme.hex(Theme.secondary) : ""
        }

        Text {
            visible: entry.plain
            anchors.left: glyph.visible ? glyph.right : parent.left
            anchors.leftMargin: glyph.visible ? 9 : 12
            anchors.right: chips.visible ? chips.left : check.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            text: entry.modelData.label || ""
            color: Theme.text
            font.family: Theme.fontFor(text)
            font.pixelSize: 14
            font.weight: entry.modelData.checked ? Font.Bold : Font.DemiBold
            elide: Text.ElideRight
        }

        Row {
            id: chips
            visible: entry.plain && entry.variants.length > 0
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            Repeater {
                model: entry.variants
                Chip {
                    required property var modelData
                    choice: modelData
                    context: entry.modelData.label || ""
                }
            }
        }

        Image {
            id: check
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 16
            height: 16
            sourceSize: Qt.size(16, 16)
            visible: entry.plain && entry.variants.length === 0 && entry.modelData.checked === true
            source: visible ? "image://icons/check/" + Theme.hex(Theme.cobaltText) + "/2.5" : ""
        }

        HoverHandler {
            id: hover
            enabled: entry.plain
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            id: tap
            enabled: entry.plain
            onTapped: function(eventPoint) {
                if (chips.visible && eventPoint.position.x >= chips.x - 2)
                    return
                var key = entry.modelData.key
                for (var i = 0; i < entry.variants.length; i++)
                    if (entry.variants[i].checked)
                        key = entry.variants[i].key
                menu.pick(key)
            }
        }
    }
}
