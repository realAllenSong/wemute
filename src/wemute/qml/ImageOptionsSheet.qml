import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Batch-level image options, reached from the image pill's "More options…".
Sheet {
    id: sheet
    width: Math.min(480, parent ? parent.width - 48 : 480)

    function sync() {
        resizeControl.current = jobController.imageResizePreset
        qualityControl.current = jobController.imageQualityPreset
        cornerControl.current = jobController.imageCornerPreset
        var size = jobController.imageTargetSizeKb
        sizeField.text = size > 0 ? String(size) : ""
    }
    onAboutToShow: sync()

    contentItem: ColumnLayout {
        spacing: 0

        Text {
            Layout.leftMargin: 28
            Layout.topMargin: 26
            text: sheet.tr("options_title")
            color: Theme.text
            font.family: Theme.font
            font.pixelSize: 22
            font.weight: Font.ExtraBold
        }
        Text {
            Layout.leftMargin: 28
            Layout.topMargin: 4
            text: sheet.tr("options_hint")
            color: Theme.muted
            font.family: Theme.font
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            Layout.rightMargin: 28
            Layout.topMargin: 22
            columns: 2
            columnSpacing: 18
            rowSpacing: 14

            Text {
                text: sheet.tr("resize")
                color: Theme.secondary
                font.family: Theme.font
                font.pixelSize: 14
                font.weight: Font.Bold
            }
            Segmented {
                id: resizeControl
                Layout.fillWidth: true
                stretch: true
                options: [
                    { "key": "original", "label": sheet.tr("opt_original") },
                    { "key": "half", "label": sheet.tr("opt_half") },
                    { "key": "edge2048", "label": sheet.tr("opt_2048") },
                    { "key": "edge1080", "label": sheet.tr("opt_1080") }
                ]
                onActivated: function(key) {
                    current = key
                    jobController.setImageResizePreset(key)
                }
            }

            Text {
                text: sheet.tr("quality")
                color: Theme.secondary
                font.family: Theme.font
                font.pixelSize: 14
                font.weight: Font.Bold
            }
            Segmented {
                id: qualityControl
                Layout.fillWidth: true
                stretch: true
                options: [
                    { "key": "small", "label": sheet.tr("opt_small") },
                    { "key": "balanced", "label": sheet.tr("opt_balanced") },
                    { "key": "best", "label": sheet.tr("opt_best") }
                ]
                onActivated: function(key) {
                    current = key
                    jobController.setImageQualityPreset(key)
                }
            }

            Text {
                text: sheet.tr("corners")
                color: Theme.secondary
                font.family: Theme.font
                font.pixelSize: 14
                font.weight: Font.Bold
            }
            Segmented {
                id: cornerControl
                Layout.fillWidth: true
                stretch: true
                options: [
                    { "key": "none", "label": sheet.tr("opt_none") },
                    { "key": "soft", "label": sheet.tr("opt_24") },
                    { "key": "round", "label": sheet.tr("opt_64") }
                ]
                onActivated: function(key) {
                    current = key
                    jobController.setImageCornerPreset(key)
                }
            }

            Text {
                text: sheet.tr("target_size")
                color: Theme.secondary
                font.family: Theme.font
                font.pixelSize: 14
                font.weight: Font.Bold
            }
            TextField {
                id: sizeField
                Layout.fillWidth: true
                implicitHeight: 36
                placeholderText: sheet.tr("off")
                placeholderTextColor: Theme.muted
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 14
                font.weight: Font.DemiBold
                font.features: { "tnum": 1 }
                leftPadding: 14
                rightPadding: 44
                inputMethodHints: Qt.ImhDigitsOnly
                validator: IntValidator { bottom: 0; top: 1000000 }
                onEditingFinished: jobController.setImageTargetSizeKb(text.length > 0 ? parseInt(text) : 0)
                background: Rectangle {
                    radius: 12
                    color: Theme.field
                    border.width: sizeField.activeFocus ? 2 : 1
                    border.color: sizeField.activeFocus ? Theme.kindLine("image") : Theme.hairline
                }
                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: sheet.tr("kb")
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            Layout.rightMargin: 24
            Layout.topMargin: 24
            Layout.bottomMargin: 24
            Text {
                Layout.fillWidth: true
                text: sheet.tr("target_size_hint")
                color: Theme.muted
                font.family: Theme.font
                font.pixelSize: 12
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            WButton {
                kind: "primary"
                text: sheet.tr("done_button")
                implicitHeight: 38
                onClicked: {
                    sizeField.editingFinished()
                    sheet.close()
                }
            }
        }
    }
}
