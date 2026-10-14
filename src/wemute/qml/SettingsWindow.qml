import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window
import "."

// ⌘, — a real settings window: icon tiles on the left, one page on the right.
// It is its own top-level window and remembers where it was left.
Window {
    id: settings
    property string page: "general"
    property int revision: 0
    property bool placed: false

    readonly property var pages: [
        { "key": "general", "label": tr("set_general"), "icon": "gear", "color": "#2C4BF0" },
        { "key": "appearance", "label": tr("set_appearance"), "icon": "contrast", "color": "#6B4FE0" },
        { "key": "convert", "label": tr("set_convert"), "icon": "convert", "color": "#0F8F7E" },
        { "key": "components", "label": tr("set_components"), "icon": "puzzle", "color": "#B7791F" },
        { "key": "integrations", "label": tr("set_integrations"), "icon": "command", "color": "#C2366B" },
        { "key": "about", "label": tr("set_about"), "icon": "info", "color": "#7D869B" }
    ]

    transientParent: null
    flags: Qt.Window | Qt.ExpandedClientAreaHint | Qt.NoTitleBarBackgroundHint
    title: tr("settings_title")
    width: 860
    height: 620
    minimumWidth: 720
    minimumHeight: 480
    color: Theme.base

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }
    function fill(key, name, value) {
        return tr(key).replace("{" + name + "}", value)
    }
    function show(name) {
        var known = false
        for (var i = 0; i < pages.length; i++)
            known = known || pages[i].key === name
        page = known ? name : (name === "ai" ? "components" : page)
        if (!placed)
            place()
        if (visibility === Window.Minimized)
            showNormal()
        else
            visible = true
        raise()
        requestActivate()
    }
    function step(delta) {
        for (var i = 0; i < pages.length; i++) {
            if (pages[i].key === page) {
                page = pages[(i + delta + pages.length) % pages.length].key
                return
            }
        }
    }

    // Back where it was left, if that spot is still on a screen.
    function place() {
        placed = true
        var saved = appSettings.windowGeometry("settings")
        if (saved.length === 4) {
            var screens = Qt.application.screens
            for (var i = 0; i < screens.length; i++) {
                var s = screens[i]
                if (saved[0] + 60 > s.virtualX && saved[0] + 60 < s.virtualX + s.width
                        && saved[1] + 20 > s.virtualY && saved[1] + 20 < s.virtualY + s.height) {
                    width = Math.max(minimumWidth, saved[2])
                    height = Math.max(minimumHeight, saved[3])
                    x = saved[0]
                    y = saved[1]
                    return
                }
            }
        }
        var owner = mainWindow
        if (owner) {
            x = owner.x + Math.round((owner.width - width) / 2)
            y = owner.y + Math.max(40, Math.round((owner.height - height) / 3))
        }
    }
    function remember() {
        if (placed && visibility !== Window.Minimized && visibility !== Window.Hidden)
            appSettings.saveWindowGeometry("settings", x, y, width, height)
    }

    property var mainWindow: null

    onXChanged: saveTimer.restart()
    onYChanged: saveTimer.restart()
    onWidthChanged: saveTimer.restart()
    onHeightChanged: saveTimer.restart()
    onClosing: remember()
    onPageChanged: {
        scroller.contentItem.contentY = 0
        if (page === "integrations")
            integrations.refresh()
    }
    Timer { id: saveTimer; interval: 400; onTriggered: settings.remember() }

    Connections {
        target: jobController
        function onPreferencesChanged() { settings.revision++ }
    }

    Shortcut {
        // The menu bar's 关闭窗口 covers this on macOS.
        enabled: !nativeMenus
        sequences: [StandardKey.Close]
        onActivated: settings.close()
    }
    Shortcut {
        sequence: "Ctrl+]"
        onActivated: settings.step(1)
    }
    Shortcut {
        sequence: "Ctrl+["
        onActivated: settings.step(-1)
    }

    FolderDialog {
        id: folderDialog
        title: settings.tr("save_to")
        onAccepted: jobController.setDestination(selectedFolder.toString())
    }

    MessageDialog {
        id: resetDialog
        title: settings.tr("reset_confirm_title")
        text: settings.tr("reset_confirm_title")
        informativeText: settings.tr("reset_confirm_text")
        buttons: MessageDialog.Reset | MessageDialog.Cancel
        onButtonClicked: function(button, role) {
            if (button === MessageDialog.Reset) {
                appSettings.reset()
                jobController.resetPreferences()
                i18n.setMode("system")
            }
        }
    }

    // ── building blocks ──────────────────────────────────────────────────

    component Heading: Text {
        color: Theme.text
        font.family: Theme.font
        font.pixelSize: 22
        font.weight: Font.ExtraBold
    }
    component Note: Text {
        Layout.fillWidth: true
        color: Theme.muted
        font.family: Theme.font
        font.pixelSize: 12
        font.weight: Font.DemiBold
        wrapMode: Text.WordWrap
        lineHeight: 1.15
    }
    // A rounded card of rows separated by hairlines.
    component Group: Rectangle {
        default property alias rows: groupColumn.data
        Layout.fillWidth: true
        implicitHeight: groupColumn.implicitHeight
        radius: 14
        color: Theme.card
        border.width: 1
        border.color: Theme.cardLine
        ColumnLayout {
            id: groupColumn
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 0
        }
    }
    component SettingRow: Item {
        id: row
        property string title: ""
        property string description: ""
        property bool divider: true
        property color descriptionColor: Theme.muted
        default property alias trailing: trailingRow.data
        Layout.fillWidth: true
        implicitHeight: Math.max(description.length > 0 ? 58 : 46, labels.implicitHeight + 22)

        Rectangle {
            visible: row.divider
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            height: 1
            color: Theme.hairline
        }
        Column {
            id: labels
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.right: trailingRow.left
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 3
            Text {
                width: parent.width
                text: row.title
                color: Theme.text
                font.family: Theme.fontFor(text)
                font.pixelSize: 13
                font.weight: Font.Bold
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                visible: row.description.length > 0
                text: row.description
                color: row.descriptionColor
                font.family: Theme.fontFor(text)
                font.pixelSize: 12
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideMiddle
            }
        }
        Row {
            id: trailingRow
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
        }
    }
    component ProgressBar_: Rectangle {
        property real value: 0
        implicitHeight: 5
        radius: 2.5
        color: Theme.track
        Rectangle {
            width: Math.max(parent.height, parent.width * parent.value)
            height: parent.height
            radius: parent.radius
            color: Theme.cobalt
        }
    }
    // A miniature window in light, dark, or half and half for 跟随系统.
    component ThemePreview: Canvas {
        property string mode: "light"
        property bool dark: Theme.dark
        onModeChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onDarkChanged: requestPaint()

        function scene(ctx, darkScene) {
            var w = width, h = height
            var bg = ctx.createLinearGradient(0, 0, w, h)
            bg.addColorStop(0, darkScene ? "#151C30" : "#EEF2FC")
            bg.addColorStop(1, darkScene ? "#0E2A2C" : "#E3F4F1")
            ctx.fillStyle = bg
            ctx.fillRect(0, 0, w, h)
            ctx.fillStyle = darkScene ? "#232C45" : "#FFFFFF"
            ctx.beginPath()
            ctx.roundedRect(w * 0.12, h * 0.16, w * 0.76, h * 0.68, 7, 7)
            ctx.fill()
            ctx.fillStyle = darkScene ? "#3550D8" : "#93A5F6"
            ctx.beginPath()
            ctx.roundedRect(w * 0.2, h * 0.3, w * 0.4, 6, 3, 3)
            ctx.fill()
            ctx.fillStyle = darkScene ? "#4A5472" : "#CDD3DF"
            ctx.beginPath()
            ctx.roundedRect(w * 0.2, h * 0.46, w * 0.26, 6, 3, 3)
            ctx.fill()
        }
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.save()
            ctx.beginPath()
            ctx.roundedRect(0, 0, width, height, 10, 10)
            ctx.clip()
            scene(ctx, mode === "dark")
            if (mode === "system") {
                ctx.beginPath()
                ctx.moveTo(width * 0.62, 0)
                ctx.lineTo(width, 0)
                ctx.lineTo(width, height)
                ctx.lineTo(width * 0.22, height)
                ctx.closePath()
                ctx.clip()
                scene(ctx, true)
            }
            ctx.restore()
        }
    }

    // ── layout ───────────────────────────────────────────────────────────

    Rectangle {
        id: sidebar
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 214
        color: Theme.dark ? "#141A2A" : "#F8FAFE"
        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.hairline
        }
        DragHandler {
            target: null
            onActiveChanged: if (active) settings.startSystemMove()
        }

        Column {
            id: nav
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 50
            anchors.leftMargin: 10
            anchors.rightMargin: 11
            spacing: 2

            Repeater {
                model: settings.pages
                Rectangle {
                    id: navItem
                    required property var modelData
                    readonly property bool selected: settings.page === modelData.key
                    width: nav.width
                    height: 32
                    radius: 8
                    color: selected ? Theme.kindTint("image") : (navHover.hovered ? Theme.hoverFill : "transparent")
                    activeFocusOnTab: true
                    Keys.onUpPressed: settings.step(-1)
                    Keys.onDownPressed: settings.step(1)
                    Keys.onSpacePressed: settings.page = modelData.key
                    Keys.onReturnPressed: settings.page = modelData.key

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -2
                        radius: parent.radius + 2
                        color: "transparent"
                        border.width: 2
                        border.color: Theme.kindLine("image")
                        visible: navItem.activeFocus
                    }
                    Rectangle {
                        id: tile
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        width: 20
                        height: 20
                        radius: 6
                        color: navItem.modelData.color
                        Image {
                            anchors.centerIn: parent
                            width: 12
                            height: 12
                            sourceSize: Qt.size(12, 12)
                            source: "image://icons/" + navItem.modelData.icon + "/ffffff/2.6"
                        }
                    }
                    Text {
                        anchors.left: tile.right
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: navItem.modelData.label
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: navItem.selected ? Font.Bold : Font.DemiBold
                    }
                    HoverHandler { id: navHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: settings.page = navItem.modelData.key }
                    Accessible.role: Accessible.PageTab
                    Accessible.name: modelData.label
                    Accessible.selected: selected
                }
            }
        }
    }

    Item {
        id: pane
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        clip: true

        Glows { anchors.fill: parent }
        DragHandler {
            target: null
            onActiveChanged: if (active) settings.startSystemMove()
        }

        ScrollView {
            id: scroller
            anchors.fill: parent
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: pageColumn
                x: 26
                width: scroller.availableWidth - 52
                spacing: 0

                Item { Layout.preferredHeight: 34 }

                // ── 通用 ─────────────────────────────────────────────────
                ColumnLayout {
                    visible: settings.page === "general"
                    Layout.fillWidth: true
                    spacing: 14
                    Heading { text: settings.tr("set_general") }
                    Group {
                        SettingRow {
                            divider: false
                            title: settings.tr("restore_session")
                            description: settings.tr("restore_session_desc")
                            Toggle {
                                checked: appSettings.restoreSession
                                onToggled: appSettings.restoreSession = checked
                                Accessible.name: settings.tr("restore_session")
                            }
                        }
                        SettingRow {
                            visible: updaterController.available
                            title: settings.tr("updates")
                            description: settings.fill("updates_desc", "version", appInfoController.version)
                            WButton {
                                text: settings.tr("check_now")
                                onClicked: updaterController.checkForUpdates()
                            }
                        }
                    }
                    Group {
                        SettingRow {
                            divider: false
                            title: settings.tr("reset_all")
                            description: settings.tr("reset_desc")
                            WButton {
                                text: settings.tr("reset_button")
                                onClicked: resetDialog.open()
                            }
                        }
                    }
                }

                // ── 外观 ─────────────────────────────────────────────────
                ColumnLayout {
                    visible: settings.page === "appearance"
                    Layout.fillWidth: true
                    spacing: 14
                    Heading { text: settings.tr("set_appearance") }
                    Group {
                        Item {
                            Layout.fillWidth: true
                            implicitHeight: previews.implicitHeight + 32
                            RowLayout {
                                id: previews
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.margins: 14
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 10
                                Repeater {
                                    model: [
                                        { "key": "system", "label": settings.tr("appearance_system") },
                                        { "key": "light", "label": settings.tr("appearance_light") },
                                        { "key": "dark", "label": settings.tr("appearance_dark") }
                                    ]
                                    Item {
                                        id: choice
                                        required property var modelData
                                        readonly property bool selected: appSettings.appearance === modelData.key
                                        Layout.fillWidth: true
                                        implicitHeight: frame.height + 30
                                        activeFocusOnTab: true
                                        Keys.onSpacePressed: appSettings.setAppearance(modelData.key)
                                        Keys.onReturnPressed: appSettings.setAppearance(modelData.key)
                                        Keys.onLeftPressed: nextItemInFocusChain(false).forceActiveFocus()
                                        Keys.onRightPressed: nextItemInFocusChain(true).forceActiveFocus()

                                        Rectangle {
                                            id: frame
                                            width: parent.width
                                            height: Math.round(width * 0.56)
                                            radius: 13
                                            color: "transparent"
                                            border.width: choice.selected ? 3 : (choice.activeFocus ? 2 : 1)
                                            border.color: choice.selected ? Theme.cobaltText
                                                : (choice.activeFocus ? Theme.kindLine("image") : Theme.cardLine)
                                            ThemePreview {
                                                anchors.fill: parent
                                                anchors.margins: 3
                                                mode: choice.modelData.key
                                            }
                                        }
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            anchors.top: frame.bottom
                                            anchors.topMargin: 9
                                            text: choice.modelData.label
                                            color: choice.selected ? Theme.cobaltText : Theme.text
                                            font.family: Theme.font
                                            font.pixelSize: 12
                                            font.weight: choice.selected ? Font.Bold : Font.DemiBold
                                        }
                                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                                        TapHandler { onTapped: appSettings.setAppearance(choice.modelData.key) }
                                        Accessible.role: Accessible.RadioButton
                                        Accessible.name: modelData.label
                                        Accessible.checked: selected
                                    }
                                }
                            }
                        }
                    }
                    Group {
                        SettingRow {
                            divider: false
                            title: settings.tr("setting_language")
                            description: settings.tr("language_desc")
                            Segmented {
                                current: i18n.mode
                                options: [
                                    { "key": "system", "label": settings.tr("follow_system") },
                                    { "key": "zh", "label": "中文" },
                                    { "key": "en", "label": "English" }
                                ]
                                onActivated: function(key) { i18n.setMode(key) }
                            }
                        }
                        SettingRow {
                            title: settings.tr("reduce_motion")
                            description: settings.tr("reduce_motion_desc")
                            Toggle {
                                checked: appSettings.reduceMotion
                                onToggled: appSettings.reduceMotion = checked
                                Accessible.name: settings.tr("reduce_motion")
                            }
                        }
                    }
                }

                // ── 转换 ─────────────────────────────────────────────────
                ColumnLayout {
                    visible: settings.page === "convert"
                    Layout.fillWidth: true
                    spacing: 14
                    Heading { text: settings.tr("set_convert") }
                    Group {
                        SettingRow {
                            divider: false
                            title: settings.tr("setting_save")
                            description: jobController.hasCustomDestination
                                ? jobController.destinationPath
                                : settings.tr("save_location_desc")
                            descriptionColor: jobController.hasCustomDestination ? Theme.secondary : Theme.muted
                            Segmented {
                                current: jobController.hasCustomDestination ? "folder" : "same"
                                options: [
                                    { "key": "same", "label": settings.tr("dest_beside") },
                                    { "key": "folder", "label": settings.tr("dest_folder") }
                                ]
                                onActivated: function(key) {
                                    if (key === "same")
                                        jobController.resetDestination()
                                    else
                                        folderDialog.open()
                                }
                            }
                            WButton {
                                visible: jobController.hasCustomDestination
                                kind: "ghost"
                                iconName: "folder-open"
                                implicitWidth: 34
                                onClicked: folderDialog.open()
                                Accessible.name: settings.tr("dest_folder")
                            }
                        }
                        SettingRow {
                            title: settings.tr("naming")
                            description: settings.fill("naming_example", "name",
                                jobController.addNameSuffix ? "IMG_0412-wemute.jpg" : "IMG_0412.jpg")
                            Segmented {
                                current: jobController.addNameSuffix ? "suffix" : "keep"
                                options: [
                                    { "key": "keep", "label": settings.tr("naming_keep") },
                                    { "key": "suffix", "label": settings.tr("naming_suffix") + " -wemute" }
                                ]
                                onActivated: function(key) { jobController.addNameSuffix = key === "suffix" }
                            }
                        }
                        SettingRow {
                            title: settings.tr("setting_auto_start")
                            Toggle {
                                checked: jobController.autoStart
                                onToggled: jobController.autoStart = checked
                                Accessible.name: settings.tr("setting_auto_start")
                            }
                        }
                        SettingRow {
                            title: settings.tr("setting_auto_reveal")
                            Toggle {
                                checked: jobController.autoReveal
                                onToggled: jobController.autoReveal = checked
                                Accessible.name: settings.tr("setting_auto_reveal")
                            }
                        }
                    }

                    Heading {
                        Layout.topMargin: 12
                        text: settings.tr("setting_formats")
                    }
                    Note {
                        Layout.topMargin: -6
                        text: settings.tr("default_formats_desc")
                    }
                    Group {
                        id: formatGroup
                        readonly property var formatRows: {
                            settings.revision
                            i18n.language
                            return jobController.defaultFormatRows()
                        }
                        readonly property int columnCount: pageColumn.width >= 600 ? 3 : 2
                        readonly property int rowCount: Math.ceil(formatRows.length / columnCount)
                        Grid {
                            id: formatGrid
                            Layout.fillWidth: true
                            columns: formatGroup.columnCount
                            Repeater {
                                model: formatGroup.formatRows
                                Item {
                                    id: cell
                                    required property var modelData
                                    required property int index
                                    readonly property int column: index % formatGroup.columnCount
                                    readonly property int line: Math.floor(index / formatGroup.columnCount)
                                    width: formatGrid.width / formatGroup.columnCount
                                    height: 50
                                    Rectangle {
                                        visible: cell.column < formatGroup.columnCount - 1
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.bottom: parent.bottom
                                        width: 1
                                        color: Theme.hairline
                                    }
                                    Rectangle {
                                        visible: cell.line < formatGroup.rowCount - 1
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: 1
                                        color: Theme.hairline
                                    }
                                    Text {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 16
                                        anchors.right: formatPill.left
                                        anchors.rightMargin: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: cell.modelData.label
                                        color: Theme.text
                                        font.family: Theme.fontFor(text)
                                        font.pixelSize: 13
                                        font.weight: Font.Bold
                                        elide: Text.ElideRight
                                    }
                                    Pill {
                                        id: formatPill
                                        anchors.right: parent.right
                                        anchors.rightMargin: 12
                                        anchors.verticalCenter: parent.verticalCenter
                                        kind: cell.modelData.kind
                                        chevron: false
                                        fontSize: 12
                                        implicitHeight: 28
                                        text: cell.modelData.valueLabel
                                        open: formatMenu.opened
                                        onClicked: formatMenu.open()
                                        Accessible.name: cell.modelData.label + " " + text
                                        PillMenu {
                                            id: formatMenu
                                            x: formatPill.width - width
                                            menuWidth: 200
                                            entries: cell.modelData.options
                                            onChosen: function(key) { jobController.setDefaultFormat(cell.modelData.kind, key) }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── 组件 ─────────────────────────────────────────────────
                ColumnLayout {
                    visible: settings.page === "components"
                    Layout.fillWidth: true
                    spacing: 14
                    Heading { text: settings.tr("set_components") }
                    Note {
                        Layout.topMargin: -6
                        text: settings.tr("components_subtitle")
                    }
                    Text {
                        Layout.topMargin: 4
                        text: settings.tr("converters")
                        color: Theme.secondary
                        font.family: Theme.font
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }
                    Group {
                        Repeater {
                            model: componentController.catalog
                            SettingRow {
                                id: componentRow
                                required property var modelData
                                required property int index
                                readonly property bool busy: modelData.installing || modelData.queued
                                divider: index > 0
                                title: modelData.name + "  " + modelData.version
                                description: modelData.error.length > 0 && !modelData.installing
                                    ? modelData.error
                                    : settings.tr("comp_desc_" + modelData.id)
                                descriptionColor: modelData.error.length > 0 && !modelData.installing ? Theme.error : Theme.muted
                                implicitHeight: Math.max(64, componentInfo.implicitHeight + 24)

                                Column {
                                    id: componentInfo
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 6
                                    Row {
                                        anchors.right: parent.right
                                        spacing: 6
                                        Tag {
                                            text: componentRow.modelData.installed ? settings.tr("installed")
                                                : (componentRow.modelData.installing
                                                    ? (componentRow.modelData.stage === "install" ? settings.tr("installing") : settings.tr("downloading"))
                                                    : (componentRow.modelData.queued ? settings.tr("queued")
                                                        : (componentRow.modelData.error.length > 0 ? settings.tr("install_failed") : settings.tr("not_installed"))))
                                            tone: componentRow.modelData.installed ? "teal" : (componentRow.busy ? "cobalt" : "neutral")
                                        }
                                        Tag {
                                            text: componentRow.modelData.installed && componentRow.modelData.diskLabel.length > 0
                                                ? componentRow.modelData.diskLabel
                                                : componentRow.modelData.sizeLabel
                                        }
                                    }
                                    ProgressBar_ {
                                        anchors.right: parent.right
                                        width: 120
                                        visible: componentRow.modelData.installing
                                        value: componentRow.modelData.progress
                                    }
                                }
                                WButton {
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: !(componentRow.modelData.installing && componentRow.modelData.stage === "install")
                                    kind: componentRow.modelData.installed ? "ghost" : (componentRow.busy ? "secondary" : "primary")
                                    iconName: componentRow.modelData.installed ? "trash" : (componentRow.busy ? "" : "download")
                                    text: componentRow.busy
                                        ? settings.tr("pause")
                                        : (componentRow.modelData.installed
                                            ? settings.tr("remove_model")
                                            : (componentRow.modelData.resumable ? settings.tr("resume") : settings.tr("get_model")))
                                    onClicked: {
                                        if (componentRow.busy)
                                            componentController.cancel(componentRow.modelData.id)
                                        else if (componentRow.modelData.installed)
                                            componentController.remove(componentRow.modelData.id)
                                        else
                                            componentController.install(componentRow.modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        Layout.topMargin: 8
                        text: settings.tr("ai_models")
                        color: Theme.secondary
                        font.family: Theme.font
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }
                    Note {
                        Layout.topMargin: -8
                        text: settings.tr("ai_subtitle")
                    }
                    Group {
                        Repeater {
                            model: aiModelController.catalog
                            SettingRow {
                                id: modelRow
                                required property var modelData
                                required property int index
                                divider: index > 0
                                title: modelData.name
                                description: modelData.description
                                implicitHeight: Math.max(64, modelInfo.implicitHeight + 24)

                                Column {
                                    id: modelInfo
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 6
                                    Row {
                                        anchors.right: parent.right
                                        spacing: 6
                                        Tag {
                                            text: modelRow.modelData.installed
                                                ? settings.tr("installed")
                                                : (modelRow.modelData.installing ? settings.tr("downloading") : settings.tr("not_installed"))
                                            tone: modelRow.modelData.installed ? "teal" : (modelRow.modelData.installing ? "cobalt" : "neutral")
                                        }
                                        Tag { text: modelRow.modelData.sizeLabel }
                                    }
                                    ProgressBar_ {
                                        anchors.right: parent.right
                                        width: 120
                                        visible: modelRow.modelData.installing
                                        value: modelRow.modelData.progress
                                    }
                                }
                                WButton {
                                    anchors.verticalCenter: parent.verticalCenter
                                    kind: modelRow.modelData.installed ? "ghost" : (modelRow.modelData.installing ? "secondary" : "primary")
                                    iconName: modelRow.modelData.installed ? "trash" : (modelRow.modelData.installing ? "" : "download")
                                    text: modelRow.modelData.installing
                                        ? settings.tr("pause")
                                        : (modelRow.modelData.installed
                                            ? settings.tr("remove_model")
                                            : (modelRow.modelData.resumable ? settings.tr("resume") : settings.tr("get_model")))
                                    onClicked: {
                                        if (modelRow.modelData.installing)
                                            aiModelController.cancelInstall()
                                        else if (modelRow.modelData.installed)
                                            aiModelController.removePackage(modelRow.modelData.id)
                                        else
                                            aiModelController.installPackage(modelRow.modelData.id)
                                    }
                                }
                            }
                        }
                    }
                    Note {
                        visible: aiModelController.lastError.length > 0
                        text: aiModelController.lastError
                        color: Theme.error
                    }
                }

                // ── 集成 ─────────────────────────────────────────────────
                ColumnLayout {
                    visible: settings.page === "integrations"
                    Layout.fillWidth: true
                    spacing: 14
                    Heading { text: settings.tr("set_integrations") }
                    Group {
                        SettingRow {
                            divider: false
                            title: settings.tr("finder_action")
                            description: integrations.finderActionsInstalled
                                ? settings.tr("finder_action_installed")
                                : settings.tr("finder_action_desc")
                            Tag {
                                anchors.verticalCenter: parent.verticalCenter
                                visible: integrations.finderActionsInstalled
                                text: settings.tr("installed")
                                tone: "teal"
                            }
                            WButton {
                                anchors.verticalCenter: parent.verticalCenter
                                enabled: integrations.finderActionAvailable
                                text: integrations.finderActionsInstalled ? settings.tr("uninstall") : settings.tr("install")
                                onClicked: integrations.finderActionsInstalled
                                    ? integrations.removeFinderActions()
                                    : integrations.installFinderActions()
                            }
                        }
                        SettingRow {
                            title: settings.tr("shortcuts_app")
                            description: settings.tr("shortcuts_app_desc")
                            WButton {
                                anchors.verticalCenter: parent.verticalCenter
                                visible: integrations.shortcutsAvailable
                                text: settings.tr("copy_command")
                                onClicked: {
                                    clipboardHelper.text = integrations.cliCommand()
                                    clipboardHelper.selectAll()
                                    clipboardHelper.copy()
                                    text = settings.tr("copied")
                                    copiedReset.restart()
                                }
                                Timer {
                                    id: copiedReset
                                    interval: 1600
                                    onTriggered: parent.text = settings.tr("copy_command")
                                }
                            }
                            WButton {
                                anchors.verticalCenter: parent.verticalCenter
                                enabled: integrations.shortcutsAvailable
                                text: settings.tr("add_to_shortcuts")
                                onClicked: integrations.installShortcut()
                            }
                        }
                    }
                    Group {
                        SettingRow {
                            divider: false
                            title: settings.tr("command_line")
                            description: integrations.commandLinePath.length > 0
                                ? settings.fill("command_line_installed", "path", integrations.commandLinePath)
                                : settings.tr("command_line_desc")
                            Tag {
                                anchors.verticalCenter: parent.verticalCenter
                                visible: integrations.commandLinePath.length > 0
                                text: settings.tr("installed")
                                tone: "teal"
                            }
                            WButton {
                                anchors.verticalCenter: parent.verticalCenter
                                text: integrations.commandLinePath.length > 0 ? settings.tr("uninstall") : settings.tr("install")
                                onClicked: integrations.commandLinePath.length > 0
                                    ? integrations.removeCommandLine()
                                    : integrations.installCommandLine()
                            }
                        }
                    }
                    Note {
                        visible: integrations.lastError.length > 0
                        text: integrations.lastError
                        color: Theme.error
                    }
                    // Copying needs a text item; it is never shown.
                    TextEdit { id: clipboardHelper; visible: false }
                    Group {
                        SettingRow {
                            id: thunderTalkRow
                            readonly property var app: integrations.thunderTalk
                            divider: false
                            title: "ThunderTalk"
                            description: settings.tr("thundertalk_desc") + "\n" + (!app.installed
                                ? settings.tr("thundertalk_missing")
                                : settings.fill("thundertalk_found", "version", app.version || "—")
                                  + " · " + settings.tr(app.cli ? "thundertalk_ready" : "thundertalk_outdated"))
                            Tag {
                                anchors.verticalCenter: parent.verticalCenter
                                text: !thunderTalkRow.app.installed ? settings.tr("not_detected")
                                    : (thunderTalkRow.app.cli ? settings.tr("connected") : settings.tr("needs_update"))
                                tone: thunderTalkRow.app.cli ? "teal" : (thunderTalkRow.app.installed ? "error" : "neutral")
                            }
                            WButton {
                                anchors.verticalCenter: parent.verticalCenter
                                visible: thunderTalkRow.app.installed === true
                                text: settings.tr("open_app")
                                onClicked: integrations.openThunderTalk()
                            }
                        }
                    }
                }

                // ── 关于 ─────────────────────────────────────────────────
                ColumnLayout {
                    visible: settings.page === "about"
                    Layout.fillWidth: true
                    spacing: 14
                    RowLayout {
                        spacing: 16
                        Image {
                            source: "../assets/brand/wemute-app-icon-1024.png"
                            sourceSize: Qt.size(144, 144)
                            Layout.preferredWidth: 72
                            Layout.preferredHeight: 72
                            mipmap: true
                        }
                        ColumnLayout {
                            spacing: 3
                            Heading { text: "Wemute" }
                            Text {
                                text: settings.tr("about_tagline")
                                color: Theme.secondary
                                font.family: Theme.font
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: settings.tr("version") + " " + appInfoController.version
                                color: Theme.muted
                                font.family: Theme.font
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                font.features: { "tnum": 1 }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: privacyRow.implicitHeight + 26
                        radius: 14
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
                            ColumnLayout {
                                spacing: 3
                                Text {
                                    text: settings.tr("privacy_title")
                                    color: Theme.text
                                    font.family: Theme.font
                                    font.pixelSize: 13
                                    font.weight: Font.Bold
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: settings.tr("privacy_note")
                                    color: Theme.secondary
                                    font.family: Theme.font
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                    Text {
                        Layout.topMargin: 6
                        text: settings.tr("third_party")
                        color: Theme.secondary
                        font.family: Theme.font
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }
                    Group {
                        Repeater {
                            model: appInfoController.thirdParty
                            SettingRow {
                                id: licenseRow
                                required property var modelData
                                required property int index
                                divider: index > 0
                                title: modelData.name + "  " + modelData.version
                                description: modelData.license
                                implicitHeight: 52
                                WButton {
                                    kind: "ghost"
                                    text: settings.tr("view_license")
                                    onClicked: appInfoController.openUrl(licenseRow.modelData.url)
                                }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        text: settings.tr("about_copyright")
                        horizontalAlignment: Text.AlignHCenter
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }

                Item { Layout.preferredHeight: 30 }
            }
        }
    }
}
