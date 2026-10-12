import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "."

// Slide-over panel: settings, AI models and about live beside the queue
// instead of replacing it.
Popup {
    id: panel
    property string tab: "general"
    signal chooseFolderRequested()

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }
    function openTab(name) {
        tab = name
        open()
    }

    parent: Overlay.overlay
    x: parent ? parent.width - width - 10 : 0
    y: 10
    width: Math.min(440, parent ? parent.width - 40 : 440)
    height: parent ? parent.height - 20 : 600
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    enter: Transition {
        NumberAnimation { property: "x"; from: panel.parent.width; to: panel.parent.width - panel.width - 10; duration: 220; easing.type: Easing.OutCubic }
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
    }
    exit: Transition {
        NumberAnimation { property: "x"; to: panel.parent.width; duration: 180; easing.type: Easing.InCubic }
        NumberAnimation { property: "opacity"; to: 0; duration: 160 }
    }

    Overlay.modal: Rectangle { color: Theme.scrim }

    background: Rectangle {
        color: Theme.canvas
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.shadow
            shadowBlur: 0.9
            shadowVerticalOffset: 6
            shadowOpacity: Theme.dark ? 0.9 : 0.55
        }
        radius: 16
        border.width: 1
        border.color: Theme.border
    }

    contentItem: ColumnLayout {
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 12
            Layout.topMargin: 16
            spacing: 10

            Text {
                text: panel.tr("nav_settings")
                color: Theme.text
                font.family: Theme.uiFont
                font.pixelSize: 17
                font.weight: Font.DemiBold
                font.letterSpacing: -0.2
                Layout.fillWidth: true
            }
            WButton {
                kind: "ghost"
                iconName: "x"
                width: 30
                height: 30
                onClicked: panel.close()
                Accessible.name: panel.tr("dismiss")
            }
        }

        Segmented {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.topMargin: 12
            stretch: true
            current: panel.tab
            options: [
                { "key": "general", "label": panel.tr("tab_general") },
                { "key": "formats", "label": panel.tr("tab_formats") },
                { "key": "ai", "label": panel.tr("tab_ai") },
                { "key": "about", "label": panel.tr("nav_about") }
            ]
            onActivated: function(key) { panel.tab = key }
        }

        ScrollView {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: 14
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: scroller.availableWidth
                spacing: 12

                // ── General ──────────────────────────────────────────────
                ColumnLayout {
                    visible: panel.tab === "general"
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    Layout.bottomMargin: 20
                    spacing: 10

                    SectionTitle { title: panel.tr("section_output") }
                    Card {
                        Layout.fillWidth: true
                        implicitHeight: outputColumn.implicitHeight
                        ColumnLayout {
                            id: outputColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            spacing: 0

                            SettingRow {
                                title: panel.tr("save_location")
                                description: jobController.hasCustomDestination
                                    ? jobController.destinationLabel
                                    : panel.tr("save_location_desc")
                                Segmented {
                                    current: jobController.hasCustomDestination ? "folder" : "same"
                                    options: [
                                        { "key": "same", "label": panel.tr("next_to_original") },
                                        { "key": "folder", "label": panel.tr("custom_folder") }
                                    ]
                                    onActivated: function(key) {
                                        if (key === "same")
                                            jobController.resetDestination()
                                        else
                                            panel.chooseFolderRequested()
                                    }
                                }
                            }
                            SettingRow {
                                title: panel.tr("auto_start_title")
                                description: panel.tr("auto_start_desc")
                                Toggle {
                                    checked: jobController.autoStart
                                    onToggled: jobController.autoStart = checked
                                }
                            }
                            SettingRow {
                                showDivider: false
                                title: panel.tr("auto_reveal_title")
                                description: panel.tr("auto_reveal_desc")
                                Toggle {
                                    checked: jobController.autoReveal
                                    onToggled: jobController.autoReveal = checked
                                }
                            }
                        }
                    }

                    SectionTitle { title: panel.tr("section_language") }
                    Card {
                        Layout.fillWidth: true
                        implicitHeight: 54
                        Segmented {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 12
                            anchors.verticalCenter: parent.verticalCenter
                            stretch: true
                            current: i18n.mode
                            options: [
                                { "key": "system", "label": panel.tr("follow_system") },
                                { "key": "zh", "label": "中文" },
                                { "key": "en", "label": "English" }
                            ]
                            onActivated: function(key) { i18n.setMode(key) }
                        }
                    }

                    SectionTitle {
                        title: panel.tr("shortcuts")
                    }
                    Card {
                        Layout.fillWidth: true
                        implicitHeight: shortcutColumn.implicitHeight + 16
                        Column {
                            id: shortcutColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 16
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 9
                            Repeater {
                                model: [
                                    ["⌘ O", "sc_add"], ["⌘ V", "sc_paste"], ["Space", "sc_preview"],
                                    ["⌫", "sc_remove"], ["↑ ↓", "sc_move"], ["⌘ ↩", "sc_convert"]
                                ]
                                Item {
                                    required property var modelData
                                    width: shortcutColumn.width
                                    height: 22
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: panel.tr(parent.modelData[1])
                                        color: Theme.secondaryText
                                        font.family: Theme.uiFont
                                        font.pixelSize: 12
                                    }
                                    Tag {
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: parent.modelData[0]
                                        mono: true
                                    }
                                }
                            }
                        }
                    }

                    SectionTitle {
                        title: panel.tr("section_updates")
                        visible: updaterController.available
                    }
                    Card {
                        visible: updaterController.available
                        Layout.fillWidth: true
                        implicitHeight: 54
                        SettingRow {
                            anchors.fill: parent
                            showDivider: false
                            title: panel.tr("version") + " " + appInfoController.version
                            WButton {
                                text: panel.tr("check_now")
                                onClicked: updaterController.checkForUpdates()
                            }
                        }
                    }
                }

                // ── Formats ──────────────────────────────────────────────
                ColumnLayout {
                    visible: panel.tab === "formats"
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    Layout.bottomMargin: 20
                    spacing: 10

                    SectionTitle {
                        title: panel.tr("section_formats")
                        description: panel.tr("section_formats_desc")
                    }
                    Card {
                        Layout.fillWidth: true
                        implicitHeight: formatColumn.implicitHeight
                        ColumnLayout {
                            id: formatColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            spacing: 0
                            Repeater {
                                model: ["image", "audio", "video"]
                                SettingRow {
                                    required property string modelData
                                    required property int index
                                    showDivider: index < 2
                                    title: panel.tr(modelData === "image" ? "images" : modelData)
                                    FormatCombo {
                                        width: 168
                                        height: 30
                                        leadingIcon: modelData === "image" ? "image" : (modelData === "audio" ? "music" : "film")
                                        model: jobController.formatOptions(modelData)
                                        currentIndex: {
                                            jobController.autoStart
                                            panel.visible
                                            return model.indexOf(jobController.defaultFormat(modelData))
                                        }
                                        onActivated: jobController.setDefaultFormat(modelData, currentText)
                                    }
                                }
                            }
                        }
                    }

                    SectionTitle {
                        title: panel.tr("section_new_images")
                        description: panel.tr("section_new_images_desc")
                    }
                    Card {
                        Layout.fillWidth: true
                        implicitHeight: imageColumn.implicitHeight
                        ColumnLayout {
                            id: imageColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            spacing: 0
                            Repeater {
                                model: [
                                    { "field": "resize", "title": "resize", "keys": ["original", "half", "edge2048", "edge1080"],
                                      "labels": ["original_size", "half_size", "long_edge_2048", "long_edge_1080"] },
                                    { "field": "quality", "title": "quality", "keys": ["small", "balanced", "best"],
                                      "labels": ["smaller", "balanced", "best_quality"] },
                                    { "field": "corners", "title": "corners", "keys": ["none", "soft", "round"],
                                      "labels": ["none", "soft_corners", "round_corners"] }
                                ]
                                SettingRow {
                                    required property var modelData
                                    required property int index
                                    showDivider: index < 2
                                    title: panel.tr(modelData.title)
                                    FormatCombo {
                                        width: 168
                                        height: 30
                                        model: modelData.labels.map(function(key) { return panel.tr(key) })
                                        currentIndex: {
                                            jobController.autoStart
                                            panel.visible
                                            return modelData.keys.indexOf(jobController.imageDefault(modelData.field))
                                        }
                                        onActivated: function(index) {
                                            jobController.setImageDefault(modelData.field, modelData.keys[index])
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── AI models ────────────────────────────────────────────
                ColumnLayout {
                    visible: panel.tab === "ai"
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    Layout.bottomMargin: 20
                    spacing: 10

                    SectionTitle {
                        title: panel.tr("ai_title")
                        description: panel.tr("ai_subtitle")
                    }

                    Repeater {
                        model: aiModelController.catalog
                        Card {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: modelColumn.implicitHeight + 28

                            ColumnLayout {
                                id: modelColumn
                                anchors.left: parent.left
                                anchors.right: modelAction.left
                                anchors.leftMargin: 16
                                anchors.rightMargin: 14
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 6

                                Text {
                                    text: modelData.name
                                    color: Theme.text
                                    font.family: Theme.uiFont
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.description
                                    color: Theme.mutedText
                                    font.family: Theme.uiFont
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Tag {
                                        text: modelData.installed
                                            ? panel.tr("installed")
                                            : (modelData.installing ? panel.tr("downloading") : panel.tr("not_installed"))
                                        tone: modelData.installed ? "green" : (modelData.installing ? "cobalt" : "neutral")
                                    }
                                    Tag { text: modelData.sizeLabel; mono: true }
                                    Tag { text: modelData.license }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 2
                                    height: 3
                                    radius: 2
                                    color: Theme.sunken
                                    visible: modelData.installing
                                    Rectangle {
                                        width: parent.width * modelData.progress
                                        height: parent.height
                                        radius: 2
                                        color: Theme.cobalt
                                    }
                                }
                            }

                            WButton {
                                id: modelAction
                                anchors.right: parent.right
                                anchors.rightMargin: 14
                                anchors.verticalCenter: parent.verticalCenter
                                kind: modelData.installed ? "ghost" : (modelData.installing ? "secondary" : "primary")
                                iconName: modelData.installed ? "trash" : (modelData.installing ? "" : "download")
                                text: modelData.installing
                                    ? panel.tr("pause")
                                    : (modelData.installed
                                        ? panel.tr("remove_model")
                                        : (modelData.resumable ? panel.tr("resume") : panel.tr("get_model")))
                                onClicked: {
                                    if (modelData.installing)
                                        aiModelController.cancelInstall()
                                    else if (modelData.installed)
                                        aiModelController.removePackage(modelData.id)
                                    else
                                        aiModelController.installPackage(modelData.id)
                                }
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: aiModelController.lastError
                        visible: text.length > 0
                        color: Theme.error
                        font.family: Theme.uiFont
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }

                // ── About ────────────────────────────────────────────────
                ColumnLayout {
                    visible: panel.tab === "about"
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    Layout.bottomMargin: 20
                    spacing: 12

                    RowLayout {
                        spacing: 14
                        Image {
                            source: "../assets/brand/wemute-app-icon-1024.png"
                            sourceSize: Qt.size(128, 128)
                            Layout.preferredWidth: 60
                            Layout.preferredHeight: 60
                            mipmap: true
                        }
                        ColumnLayout {
                            spacing: 3
                            Text {
                                text: "Wemute"
                                color: Theme.text
                                font.family: Theme.uiFont
                                font.pixelSize: 20
                                font.weight: Font.Bold
                                font.letterSpacing: -0.3
                            }
                            Text {
                                text: panel.tr("about_tagline")
                                color: Theme.secondaryText
                                font.family: Theme.uiFont
                                font.pixelSize: 12
                            }
                            Text {
                                text: panel.tr("version") + " " + appInfoController.version
                                color: Theme.mutedText
                                font.family: Theme.monoFont
                                font.features: { "tnum": 1 }
                                font.pixelSize: 11
                            }
                        }
                    }

                    Card {
                        Layout.fillWidth: true
                        implicitHeight: privacyRow.implicitHeight + 24
                        RowLayout {
                            id: privacyRow
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 14
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10
                            Image {
                                Layout.alignment: Qt.AlignTop
                                Layout.preferredWidth: 16
                                Layout.preferredHeight: 16
                                sourceSize: Qt.size(16, 16)
                                source: "image://icons/lock/" + Theme.hex(Theme.cobalt)
                            }
                            Text {
                                Layout.fillWidth: true
                                text: panel.tr("privacy_note")
                                color: Theme.secondaryText
                                font.family: Theme.uiFont
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    SectionTitle { title: panel.tr("third_party") }
                    Card {
                        Layout.fillWidth: true
                        implicitHeight: thirdPartyColumn.implicitHeight
                        Column {
                            id: thirdPartyColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            Repeater {
                                model: appInfoController.thirdParty
                                Item {
                                    required property var modelData
                                    required property int index
                                    width: thirdPartyColumn.width
                                    height: 50
                                    Column {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 16
                                        anchors.right: licenseButton.left
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 3
                                        Text {
                                            width: parent.width
                                            text: modelData.name + "  " + modelData.version
                                            color: Theme.text
                                            font.family: Theme.uiFont
                                            font.pixelSize: 12
                                            font.weight: Font.Medium
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            width: parent.width
                                            text: modelData.license
                                            color: Theme.mutedText
                                            font.family: Theme.uiFont
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                    WButton {
                                        id: licenseButton
                                        anchors.right: parent.right
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        kind: "ghost"
                                        height: 28
                                        text: panel.tr("view_license")
                                        onClicked: appInfoController.openUrl(modelData.url)
                                    }
                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 16
                                        anchors.bottom: parent.bottom
                                        height: 1
                                        color: Theme.hairline
                                        visible: index < appInfoController.thirdParty.length - 1
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: panel.tr("about_copyright")
                        horizontalAlignment: Text.AlignHCenter
                        color: Theme.mutedText
                        font.family: Theme.uiFont
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
