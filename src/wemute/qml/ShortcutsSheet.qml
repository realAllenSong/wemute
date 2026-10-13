import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// 帮助 → 快捷键.
Sheet {
    id: sheet
    width: 420

    readonly property var rows: [
        { "keys": "⌘O", "label": tr("sc_add") },
        { "keys": "⌘V", "label": tr("sc_paste") },
        { "keys": "⌘K", "label": tr("sc_search") },
        { "keys": "⏎", "label": tr("sc_convert") },
        { "keys": "Space", "label": tr("sc_preview") },
        { "keys": "← → ↑ ↓", "label": tr("sc_move") },
        { "keys": "⌫", "label": tr("sc_remove") },
        { "keys": "⌘⌫", "label": tr("sc_clear") },
        { "keys": "⌘Z", "label": tr("sc_undo") },
        { "keys": "⌘,", "label": tr("sc_settings") }
    ]

    contentItem: ColumnLayout {
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 26
            Layout.rightMargin: 16
            Layout.topMargin: 20
            Layout.bottomMargin: 8
            Text {
                Layout.fillWidth: true
                text: sheet.tr("shortcuts_title")
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 20
                font.weight: Font.ExtraBold
            }
            WButton {
                kind: "ghost"
                iconName: "x"
                implicitWidth: 34
                onClicked: sheet.close()
                Accessible.name: sheet.tr("dismiss")
            }
        }

        Repeater {
            model: sheet.rows
            Item {
                required property var modelData
                required property int index
                Layout.fillWidth: true
                Layout.leftMargin: 26
                Layout.rightMargin: 26
                implicitHeight: 40
                Rectangle {
                    visible: parent.index > 0
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 1
                    color: Theme.hairline
                }
                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: parent.modelData.label
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }
                Rectangle {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: keyText.implicitWidth + 16
                    height: 24
                    radius: 7
                    color: Theme.field
                    border.width: 1
                    border.color: Theme.hairline
                    Text {
                        id: keyText
                        anchors.centerIn: parent
                        text: parent.parent.modelData.keys
                        color: Theme.secondary
                        font.family: Theme.latinFont
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }
                }
            }
        }

        Item { Layout.preferredHeight: 18 }
    }
}
