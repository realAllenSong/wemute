import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// ⌘, — save location, default formats, language, auto-start; AI models and
// About live in secondary tabs.
Sheet {
    id: panel
    property string tab: "general"
    property int revision: 0
    signal chooseFolderRequested()

    function openTab(name) {
        tab = name
        open()
    }

    width: Math.min(580, parent ? parent.width - 48 : 580)
    height: Math.min(600, parent ? parent.height - 48 : 600)

    Connections {
        target: jobController
        function onPreferencesChanged() { panel.revision++ }
    }

    component RowLabel: Text {
        color: Theme.text
        font.family: Theme.font
        font.pixelSize: 15
        font.weight: Font.Bold
    }
    component Divider: Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: Theme.hairline
    }

    contentItem: ColumnLayout {
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            Layout.rightMargin: 20
            Layout.topMargin: 22
            spacing: 12
            Text {
                Layout.fillWidth: true
                text: panel.tr("nav_settings")
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 22
                font.weight: Font.ExtraBold
            }
            WButton {
                kind: "ghost"
                iconName: "x"
                implicitWidth: 34
                onClicked: panel.close()
                Accessible.name: panel.tr("dismiss")
            }
        }

        Segmented {
            Layout.leftMargin: 28
            Layout.topMargin: 14
            // "ai" is the older name of the components tab.
            current: panel.tab === "ai" ? "components" : panel.tab
            options: [
                { "key": "general", "label": panel.tr("tab_general") },
                { "key": "components", "label": panel.tr("tab_components") },
                { "key": "about", "label": panel.tr("nav_about") }
            ]
            onActivated: function(key) { panel.tab = key }
        }

        ScrollView {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: 10
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: scroller.availableWidth
                spacing: 0

                // ── General ──────────────────────────────────────────────
                ColumnLayout {
                    visible: panel.tab === "general"
                    Layout.fillWidth: true
                    Layout.leftMargin: 28
                    Layout.rightMargin: 28
                    Layout.bottomMargin: 20
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        spacing: 16
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            RowLabel { text: panel.tr("setting_save") }
                            Text {
                                Layout.fillWidth: true
                                text: jobController.hasCustomDestination
                                    ? jobController.destinationLabel
                                    : panel.tr("save_location_desc")
                                color: Theme.muted
                                font.family: Theme.font
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                elide: Text.ElideMiddle
                            }
                        }
                        Segmented {
                            current: jobController.hasCustomDestination ? "folder" : "same"
                            options: [
                                { "key": "same", "label": panel.tr("dest_same") },
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
                    Divider { }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        spacing: 10
                        RowLabel {
                            Layout.fillWidth: true
                            text: panel.tr("setting_formats")
                        }
                        Repeater {
                            model: ["image", "video", "audio"]
                            Pill {
                                id: formatPill
                                required property string modelData
                                kind: modelData
                                fontSize: 14
                                implicitHeight: 36
                                text: {
                                    panel.revision
                                    return jobController.defaultFormat(modelData)
                                }
                                open: formatMenu.opened
                                onClicked: formatMenu.open()
                                Accessible.name: panel.tr(modelData === "image" ? "images" : modelData) + " " + text
                                PillMenu {
                                    id: formatMenu
                                    menuWidth: 200
                                    entries: {
                                        panel.revision
                                        var current = jobController.defaultFormat(formatPill.modelData)
                                        return jobController.formatOptions(formatPill.modelData).map(function(option) {
                                            return { "key": option, "label": option, "checked": option === current }
                                        })
                                    }
                                    onChosen: function(key) { jobController.setDefaultFormat(formatPill.modelData, key) }
                                }
                            }
                        }
                    }
                    Divider { }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        RowLabel {
                            Layout.fillWidth: true
                            text: panel.tr("setting_language")
                        }
                        Segmented {
                            current: i18n.mode
                            options: [
                                { "key": "system", "label": panel.tr("follow_system") },
                                { "key": "zh", "label": "中文" },
                                { "key": "en", "label": "English" }
                            ]
                            onActivated: function(key) { i18n.setMode(key) }
                        }
                    }
                    Divider { }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        RowLabel {
                            Layout.fillWidth: true
                            text: panel.tr("setting_auto_start")
                        }
                        Toggle {
                            checked: jobController.autoStart
                            onToggled: jobController.autoStart = checked
                            Accessible.name: panel.tr("setting_auto_start")
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52
                        RowLabel {
                            Layout.fillWidth: true
                            text: panel.tr("setting_auto_reveal")
                            color: Theme.secondary
                            font.pixelSize: 14
                        }
                        Toggle {
                            checked: jobController.autoReveal
                            onToggled: jobController.autoReveal = checked
                            Accessible.name: panel.tr("setting_auto_reveal")
                        }
                    }
                }

                // ── Components: converters, then AI models ───────────────
                ColumnLayout {
                    visible: panel.tab === "ai" || panel.tab === "components"
                    Layout.fillWidth: true
                    Layout.leftMargin: 28
                    Layout.rightMargin: 28
                    Layout.topMargin: 8
                    Layout.bottomMargin: 20
                    spacing: 12

                    Text {
                        Layout.fillWidth: true
                        text: panel.tr("components_subtitle")
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    RowLabel {
                        Layout.topMargin: 4
                        text: panel.tr("converters")
                        font.pixelSize: 14
                    }

                    Repeater {
                        model: componentController.catalog
                        Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: componentColumn.implicitHeight + 28
                            radius: 18
                            color: Theme.card
                            border.width: 1
                            border.color: Theme.cardLine

                            ColumnLayout {
                                id: componentColumn
                                anchors.left: parent.left
                                anchors.right: componentAction.left
                                anchors.leftMargin: 18
                                anchors.rightMargin: 14
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 6

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name + "  " + modelData.version
                                    color: Theme.text
                                    font.family: Theme.font
                                    font.pixelSize: 15
                                    font.weight: Font.Bold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: panel.tr("comp_desc_" + modelData.id)
                                    color: Theme.muted
                                    font.family: Theme.font
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Tag {
                                        text: modelData.installed ? panel.tr("installed")
                                            : (modelData.installing
                                                ? (modelData.stage === "install" ? panel.tr("installing") : panel.tr("downloading"))
                                                : (modelData.queued ? panel.tr("queued")
                                                    : (modelData.error.length > 0 ? panel.tr("install_failed") : panel.tr("not_installed"))))
                                        tone: modelData.installed ? "teal" : (modelData.installing || modelData.queued ? "cobalt" : "neutral")
                                    }
                                    Tag {
                                        text: modelData.installed && modelData.diskLabel.length > 0
                                            ? panel.tr("on_disk").replace("{size}", modelData.diskLabel)
                                            : panel.tr("download_size").replace("{size}", modelData.sizeLabel)
                                    }
                                    Tag { text: modelData.license }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 2
                                    implicitHeight: 6
                                    radius: 3
                                    color: Theme.track
                                    visible: modelData.installing
                                    Rectangle {
                                        width: parent.width * modelData.progress
                                        height: parent.height
                                        radius: 3
                                        color: Theme.cobalt
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    visible: modelData.error.length > 0 && !modelData.installing
                                    text: modelData.error
                                    color: Theme.error
                                    font.family: Theme.font
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                }
                            }

                            WButton {
                                id: componentAction
                                anchors.right: parent.right
                                anchors.rightMargin: 14
                                anchors.verticalCenter: parent.verticalCenter
                                readonly property bool busy: modelData.installing || modelData.queued
                                visible: !(modelData.installing && modelData.stage === "install")
                                kind: modelData.installed ? "ghost" : (busy ? "secondary" : "primary")
                                iconName: modelData.installed ? "trash" : (busy ? "" : "download")
                                text: busy
                                    ? panel.tr("pause")
                                    : (modelData.installed
                                        ? panel.tr("remove_model")
                                        : (modelData.resumable ? panel.tr("resume") : panel.tr("get_model")))
                                onClicked: {
                                    if (busy)
                                        componentController.cancel(modelData.id)
                                    else if (modelData.installed)
                                        componentController.remove(modelData.id)
                                    else
                                        componentController.install(modelData.id)
                                }
                            }
                        }
                    }

                    RowLabel {
                        Layout.topMargin: 10
                        text: panel.tr("ai_models")
                        font.pixelSize: 14
                    }

                    Text {
                        Layout.fillWidth: true
                        text: panel.tr("ai_subtitle")
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: aiModelController.catalog
                        Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: modelColumn.implicitHeight + 28
                            radius: 18
                            color: Theme.card
                            border.width: 1
                            border.color: Theme.cardLine

                            ColumnLayout {
                                id: modelColumn
                                anchors.left: parent.left
                                anchors.right: modelAction.left
                                anchors.leftMargin: 18
                                anchors.rightMargin: 14
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 6

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: Theme.text
                                    font.family: Theme.font
                                    font.pixelSize: 15
                                    font.weight: Font.Bold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.description
                                    color: Theme.muted
                                    font.family: Theme.font
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Tag {
                                        text: modelData.installed
                                            ? panel.tr("installed")
                                            : (modelData.installing ? panel.tr("downloading") : panel.tr("not_installed"))
                                        tone: modelData.installed ? "teal" : (modelData.installing ? "cobalt" : "neutral")
                                    }
                                    Tag { text: modelData.sizeLabel }
                                    Tag { text: modelData.license }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 2
                                    implicitHeight: 6
                                    radius: 3
                                    color: Theme.track
                                    visible: modelData.installing
                                    Rectangle {
                                        width: parent.width * modelData.progress
                                        height: parent.height
                                        radius: 3
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
                        font.family: Theme.font
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                }

                // ── About ────────────────────────────────────────────────
                ColumnLayout {
                    visible: panel.tab === "about"
                    Layout.fillWidth: true
                    Layout.leftMargin: 28
                    Layout.rightMargin: 28
                    Layout.topMargin: 10
                    Layout.bottomMargin: 20
                    spacing: 14

                    RowLayout {
                        spacing: 16
                        Image {
                            source: "../assets/brand/wemute-app-icon-1024.png"
                            sourceSize: Qt.size(128, 128)
                            Layout.preferredWidth: 64
                            Layout.preferredHeight: 64
                            mipmap: true
                        }
                        ColumnLayout {
                            spacing: 3
                            Text {
                                text: "Wemute"
                                color: Theme.text
                                font.family: Theme.font
                                font.pixelSize: 22
                                font.weight: Font.ExtraBold
                            }
                            Text {
                                text: panel.tr("about_tagline")
                                color: Theme.secondary
                                font.family: Theme.font
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: panel.tr("version") + " " + appInfoController.version
                                color: Theme.muted
                                font.family: Theme.font
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                font.features: { "tnum": 1 }
                            }
                        }
                        Item { Layout.fillWidth: true }
                        WButton {
                            visible: updaterController.available
                            text: panel.tr("check_now")
                            onClicked: updaterController.checkForUpdates()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: privacyRow.implicitHeight + 28
                        radius: 18
                        color: Theme.kindTint("image")
                        RowLayout {
                            id: privacyRow
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 16
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10
                            Image {
                                Layout.alignment: Qt.AlignTop
                                Layout.preferredWidth: 16
                                Layout.preferredHeight: 16
                                sourceSize: Qt.size(16, 16)
                                source: "image://icons/lock/" + Theme.hex(Theme.cobaltText) + "/2"
                            }
                            Text {
                                Layout.fillWidth: true
                                text: panel.tr("privacy_note")
                                color: Theme.secondary
                                font.family: Theme.font
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Text {
                        Layout.topMargin: 4
                        text: panel.tr("third_party")
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 14
                        font.weight: Font.Bold
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: thirdPartyColumn.implicitHeight
                        radius: 18
                        color: Theme.card
                        border.width: 1
                        border.color: Theme.cardLine
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
                                    height: 52
                                    Column {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 18
                                        anchors.right: licenseButton.left
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 3
                                        Text {
                                            width: parent.width
                                            text: modelData.name + "  " + modelData.version
                                            color: Theme.text
                                            font.family: Theme.font
                                            font.pixelSize: 13
                                            font.weight: Font.Bold
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            width: parent.width
                                            text: modelData.license
                                            color: Theme.muted
                                            font.family: Theme.font
                                            font.pixelSize: 11
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                    }
                                    WButton {
                                        id: licenseButton
                                        anchors.right: parent.right
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        kind: "ghost"
                                        text: panel.tr("view_license")
                                        onClicked: appInfoController.openUrl(modelData.url)
                                    }
                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 18
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
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }
            }
        }
    }
}
