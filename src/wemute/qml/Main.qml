import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.qmlmodels
import "."

// "Ice": drop files, then read one sentence that says what will happen.
ApplicationWindow {
    id: window
    width: Math.max(minimumWidth, Math.min(1040, Math.round(Screen.desktopAvailableWidth * 0.8)))
    height: Math.max(minimumHeight, Math.min(680, Math.round(Screen.desktopAvailableHeight * 0.8)))
    minimumWidth: 760
    minimumHeight: 540
    visible: true
    flags: Qt.Window | Qt.ExpandedClientAreaHint | Qt.NoTitleBarBackgroundHint
    title: jobController.busy && jobController.progressText.length > 0
        ? "Wemute — " + jobController.progressText
        : "Wemute"
    color: Theme.base
    font.family: Theme.font
    // Content runs under the transparent title bar; layout leaves room itself.
    topPadding: 0
    leftPadding: 0
    rightPadding: 0
    bottomPadding: 0
    background: Glows { }

    readonly property string phase: jobController.phase

    Binding { target: Theme; property: "language"; value: i18n.language }
    readonly property bool running: phase === "running"
    // Height of the native title bar row that holds the traffic lights.
    readonly property int chromeHeight: 28
    readonly property int sentenceSize: glass.width < 820 ? 26 : 30
    readonly property int lineHeight: Math.round(sentenceSize * 1.75)
    property int openMenus: 0
    property bool showSelection: false
    readonly property bool hasPopupOpen: openMenus > 0 || settingsPanel.opened
        || imageOptionsPopup.opened || eraseMaskPopup.opened
    readonly property int columns: cardFlow.columns

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }
    function primaryAction() {
        if (phase === "ready")
            jobController.startAll()
        else if (phase === "done" && jobController.doneCount > 0)
            jobController.revealOutputs()
    }
    function moveSelection(step) {
        showSelection = true
        jobController.moveSelection(step)
    }

    Shortcut {
        sequences: [StandardKey.Open]
        onActivated: fileDialog.open()
    }
    Shortcut {
        sequences: [StandardKey.Paste]
        enabled: !window.hasPopupOpen
        onActivated: jobController.pasteFiles()
    }
    Shortcut {
        sequences: [StandardKey.Preferences]
        onActivated: settingsPanel.openTab("general")
    }
    Shortcut {
        sequences: ["Return", "Enter"]
        enabled: (window.phase === "ready" || window.phase === "done") && !window.hasPopupOpen
        onActivated: window.primaryAction()
    }
    Shortcut {
        sequence: "Space"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: jobController.quickLookSelected()
    }
    Shortcut {
        sequences: ["Backspace", "Delete"]
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: jobController.removeSelected()
    }
    Shortcut {
        sequence: "Left"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: window.moveSelection(-1)
    }
    Shortcut {
        sequence: "Right"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: window.moveSelection(1)
    }
    Shortcut {
        sequence: "Up"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: window.moveSelection(-window.columns)
    }
    Shortcut {
        sequence: "Down"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: window.moveSelection(window.columns)
    }

    Connections {
        target: jobController
        function onEraseMaskRequested(jobId, sourceUrl, applyGroup) {
            eraseMaskPopup.openFor(jobId, sourceUrl, applyGroup)
        }
        function onBatchFinished(succeeded, failed) {
            // Bounce the Dock icon when the user switched away during a long batch.
            if (!window.active)
                window.alert(0)
        }
    }

    FileDialog {
        id: fileDialog
        title: window.tr("choose_files")
        fileMode: FileDialog.OpenFiles
        onAccepted: jobController.addUrls(selectedFiles)
    }

    FolderDialog {
        id: folderDialog
        title: window.tr("save_to")
        onAccepted: jobController.setDestination(selectedFolder.toString())
    }

    // ── title bar ────────────────────────────────────────────────────────

    Item {
        id: titleBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: window.chromeHeight + 14
        z: 4

        DragHandler {
            target: null
            onActiveChanged: if (active) window.startSystemMove()
        }
        TapHandler {
            onDoubleTapped: window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: window.chromeHeight / 2
            visible: window.phase !== "empty"
            text: "Wemute"
            color: Theme.title
            font.family: Theme.font
            font.pixelSize: 14
            font.weight: Font.Bold
        }

        WButton {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: window.chromeHeight / 2 + 1
            kind: "ghost"
            iconName: "gear"
            iconSize: 16
            implicitWidth: 30
            implicitHeight: 28
            opacity: hovered ? 1 : 0.75
            onClicked: settingsPanel.openTab("general")
            Accessible.name: window.tr("nav_settings")
            ToolTip.visible: hovered
            ToolTip.delay: 600
            ToolTip.text: window.tr("nav_settings") + "  ⌘,"
        }
    }

    // ── ① empty ──────────────────────────────────────────────────────────

    Item {
        id: emptyStage
        anchors.fill: parent
        anchors.topMargin: titleBar.height
        visible: window.phase === "empty"

        HoverHandler { cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: fileDialog.open() }

        Column {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -titleBar.height / 2
            spacing: 0

            Item {
                id: bubble
                anchors.horizontalCenter: parent.horizontalCenter
                width: 150
                height: 150
                rotation: -6
                scale: dropArea.containsDrag ? 1.07 : 1
                Behavior on scale { NumberAnimation { duration: 260; easing.type: Easing.OutBack } }

                RectangularShadow {
                    anchors.fill: parent
                    offset.y: 24
                    blur: dropArea.containsDrag ? 60 : 50
                    spread: -20
                    radius: 44
                    color: Qt.rgba(44 / 255, 75 / 255, 240 / 255, Theme.dark ? 0.55 : 0.5)
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 44
                    antialiasing: true
                    gradient: Gradient {
                        GradientStop { position: 0; color: Theme.dark ? "#232B44" : "#FFFFFF" }
                        GradientStop { position: 1; color: Theme.dark ? "#1A2138" : "#EEF2FF" }
                    }
                    border.width: 1
                    border.color: Theme.dark ? Qt.rgba(1, 1, 1, 0.08) : "#FFFFFF"
                }
                Image {
                    anchors.centerIn: parent
                    rotation: 6
                    width: 64
                    height: 64
                    sourceSize: Qt.size(64, 64)
                    source: "image://icons/download/" + Theme.hex(Theme.cobaltText) + "/1.8"
                }
            }

            Item { width: 1; height: 34 }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: jobController.probing
                    ? window.tr("reading_files")
                    : (dropArea.containsDrag ? window.tr("drop_title_active") : window.tr("ice_drop_title"))
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 32
                font.weight: Font.ExtraBold
            }

            Item { width: 1; height: 8 }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: window.tr("ice_drop_sub")
                color: Theme.dark ? Theme.muted : "#6B7489"
                font.family: Theme.font
                font.pixelSize: 16
                font.weight: Font.DemiBold
            }

            Item { width: 1; height: 18; visible: emptyNotice.visible }

            NoticeLine {
                id: emptyNotice
                anchors.horizontalCenter: parent.horizontalCenter
                maxWidth: emptyStage.width - 120
            }
        }
    }

    // ── ② ready · ③ running → done ───────────────────────────────────────

    Item {
        id: glassFrame
        anchors.fill: parent
        anchors.topMargin: titleBar.height + 6
        anchors.leftMargin: 28
        anchors.rightMargin: 28
        anchors.bottomMargin: 28
        visible: window.phase !== "empty"

        // The glass is translucent, so its shadow is cut out underneath it.
        Item {
            id: panelShadow
            anchors.fill: parent
            anchors.margins: -90
            layer.enabled: true
            layer.effect: MultiEffect {
                maskEnabled: true
                maskInverted: true
                maskSource: panelShadowMask
            }
            RectangularShadow {
                anchors.fill: parent
                anchors.margins: 90
                offset.y: 30
                blur: 60
                spread: -30
                radius: Theme.radiusPanel
                color: Theme.panelShadow
            }
        }
        Item {
            id: panelShadowMask
            anchors.fill: panelShadow
            visible: false
            layer.enabled: true
            Rectangle {
                anchors.fill: parent
                anchors.margins: 90
                radius: Theme.radiusPanel
            }
        }
        // Glows cobalt while files are dragged over the window.
        RectangularShadow {
            anchors.fill: glass
            blur: 26
            spread: 2
            radius: Theme.radiusPanel
            color: Qt.rgba(61 / 255, 92 / 255, 1, Theme.dark ? 0.55 : 0.35)
            opacity: dropArea.containsDrag ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 140 } }
        }

        Rectangle {
            id: glass
            anchors.fill: parent
            radius: Theme.radiusPanel
            color: Theme.panel
            border.width: dropArea.containsDrag ? 2 : 1
            border.color: dropArea.containsDrag ? Theme.cobaltText : Theme.panelLine
        }

        Item {
            id: content
            anchors.fill: parent
            anchors.leftMargin: 40
            anchors.rightMargin: 40
            anchors.topMargin: 30

            Column {
                id: header
                width: parent.width
                spacing: 0

                // The sentence.
                Column {
                    id: sentence
                    width: parent.width
                    visible: window.phase === "ready" || window.phase === "running"
                    spacing: 0

                    Repeater {
                        model: jobController.groups

                        Flow {
                            id: line
                            required property var modelData
                            width: sentence.width
                            spacing: 12

                            Word { text: window.tr("sentence_lead") }
                            Word { text: line.modelData.countLabel; strong: true }
                            Word { text: window.tr("sentence_to") }
                            Item {
                                width: formatPill.width
                                height: window.lineHeight
                                Pill {
                                    id: formatPill
                                    anchors.verticalCenter: parent.verticalCenter
                                    kind: line.modelData.kind
                                    fontSize: window.sentenceSize
                                    enabled: !window.running
                                    open: formatMenu.opened
                                    text: line.modelData.target.length > 0 ? line.modelData.target : window.tr("mixed_formats")
                                    onClicked: formatMenu.open()
                                    Accessible.name: line.modelData.countLabel + " → " + text
                                    PillMenu {
                                        id: formatMenu
                                        onOpened: window.openMenus++
                                        onClosed: window.openMenus--
                                        entries: {
                                            var plain = jobController.formatOptions(line.modelData.kind)
                                            var list = line.modelData.options.map(function(option) {
                                                return {
                                                    "key": option,
                                                    "label": option,
                                                    "checked": option === line.modelData.target,
                                                    "icon": plain.indexOf(option) < 0 ? "sparkles" : ""
                                                }
                                            })
                                            if (line.modelData.kind === "image") {
                                                list.push({ "separator": true })
                                                list.push({ "key": "__options", "label": window.tr("more_options"), "icon": "settings" })
                                            }
                                            return list
                                        }
                                        onChosen: function(key) {
                                            if (key === "__options")
                                                imageOptionsPopup.open()
                                            else
                                                jobController.setGroupTargetFormat(line.modelData.kind, key)
                                        }
                                    }
                                }
                            }
                            Item {
                                visible: line.modelData.extra.length > 0
                                width: extraRow.width
                                height: window.lineHeight
                                Row {
                                    id: extraRow
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 6
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: window.tr("sentence_joiner")
                                        color: Theme.muted
                                        font.family: Theme.font
                                        font.pixelSize: window.sentenceSize
                                        font.weight: Font.Bold
                                    }
                                    Pill {
                                        anchors.verticalCenter: parent.verticalCenter
                                        kind: "image"
                                        chevron: false
                                        fontSize: window.sentenceSize - 6
                                        implicitHeight: 38
                                        enabled: !window.running
                                        text: line.modelData.extra
                                        onClicked: imageOptionsPopup.open()
                                    }
                                }
                            }
                        }
                    }

                    Item { width: 1; height: 10 }

                    // "Save to [Same folder ▾]" with the primary button on the right.
                    Item {
                        width: sentence.width
                        height: Math.max(destinationFlow.height, actionButton.height)

                        Flow {
                            id: destinationFlow
                            anchors.left: parent.left
                            anchors.right: actionButton.left
                            anchors.rightMargin: 20
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 12

                            Word { text: window.tr("sentence_save") }
                            Item {
                                width: destinationPill.width
                                height: window.lineHeight
                                Pill {
                                    id: destinationPill
                                    anchors.verticalCenter: parent.verticalCenter
                                    kind: "neutral"
                                    fontSize: window.sentenceSize
                                    enabled: !window.running
                                    open: destinationMenu.opened
                                    text: jobController.hasCustomDestination ? jobController.destinationLabel : window.tr("dest_same")
                                    onClicked: destinationMenu.open()
                                    PillMenu {
                                        id: destinationMenu
                                        onOpened: window.openMenus++
                                        onClosed: window.openMenus--
                                        entries: {
                                            var list = [{ "key": "same", "label": window.tr("dest_same"), "checked": !jobController.hasCustomDestination }]
                                            if (jobController.hasCustomDestination)
                                                list.push({ "key": "current", "label": jobController.destinationLabel, "checked": true, "icon": "folder" })
                                            if (jobController.hasRecentDestination)
                                                list.push({ "key": "recent", "label": jobController.recentDestinationLabel, "icon": "folder" })
                                            list.push({ "separator": true })
                                            list.push({ "key": "other", "label": window.tr("dest_other"), "icon": "folder-open" })
                                            return list
                                        }
                                        onChosen: function(key) {
                                            if (key === "same")
                                                jobController.resetDestination()
                                            else if (key === "recent")
                                                jobController.useRecentDestination()
                                            else if (key === "other")
                                                folderDialog.open()
                                        }
                                    }
                                }
                            }
                        }

                        IceButton {
                            id: actionButton
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            kind: window.running ? "secondary" : "primary"
                            text: window.running ? window.tr("stop") : window.tr("start_convert")
                            trailingIcon: window.running ? "" : "arrow-right"
                            enabled: window.running || jobController.pendingCount > 0
                            onClicked: window.running ? jobController.cancelAll() : jobController.startAll()
                            ToolTip.visible: hovered && !window.running
                            ToolTip.delay: 800
                            ToolTip.text: "⏎"
                        }
                    }

                    // Running: a thick rounded meter with "Converting 8 of 12".
                    Item {
                        width: sentence.width
                        height: window.running ? 52 : 0
                        visible: window.running
                        Rectangle {
                            id: meter
                            y: 16
                            width: parent.width
                            height: 10
                            radius: 6
                            color: Theme.track
                            Rectangle {
                                height: parent.height
                                radius: 6
                                width: Math.max(height, parent.width * jobController.overallProgress)
                                Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: Theme.gradientTop }
                                    GradientStop { position: 1; color: Theme.meterEnd }
                                }
                            }
                        }
                        Text {
                            anchors.top: meter.bottom
                            anchors.topMargin: 10
                            text: jobController.progressText
                            color: Theme.secondary
                            font.family: Theme.font
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            font.features: { "tnum": 1 }
                        }
                    }
                }

                // Done: headline, savings, and the two actions.
                Column {
                    id: doneHeader
                    width: parent.width
                    visible: window.phase === "done"
                    spacing: 0

                    Text {
                        width: parent.width
                        text: jobController.doneTitle
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 34
                        font.weight: Font.ExtraBold
                        font.features: { "pnum": 1 }
                        elide: Text.ElideRight
                    }
                    Item { width: 1; height: 6 }
                    Row {
                        visible: jobController.savingsAmount.length > 0
                        spacing: 0
                        Text {
                            text: jobController.savingsLead
                            color: Theme.secondary
                            font.family: Theme.font
                            font.pixelSize: 17
                            font.weight: Font.DemiBold
                        }
                        Text {
                            text: jobController.savingsAmount
                            color: jobController.savingsPositive ? Theme.teal : Theme.text
                            font.family: Theme.font
                            font.pixelSize: 17
                            font.weight: Font.Bold
                            font.features: { "tnum": 1 }
                        }
                    }
                    Item { width: 1; height: 26 }
                    Row {
                        spacing: 12
                        IceButton {
                            visible: jobController.doneCount > 0
                            kind: "primary"
                            text: window.tr("show_results")
                            onClicked: jobController.revealOutputs()
                        }
                        IceButton {
                            kind: "secondary"
                            text: window.tr("new_batch")
                            onClicked: jobController.newBatch()
                        }
                        Item {
                            visible: jobController.failedCount > 0
                            width: retryPill.width + 4
                            height: Theme.buttonHeight
                            Pill {
                                id: retryPill
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                kind: "error"
                                chevron: false
                                fontSize: 16
                                text: jobController.retryLabel
                                onClicked: jobController.retryFailed()
                            }
                        }
                    }
                }

                Item { width: 1; height: 14; visible: panelNotice.visible }
                NoticeLine {
                    id: panelNotice
                    maxWidth: header.width
                }
            }

            // Soft top and bottom edges where cards scroll out of view.
            Item {
                id: cardFade
                anchors.fill: cardScroller
                visible: false
                layer.enabled: true
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: cardScroller.atYBeginning ? "white" : "transparent" }
                        GradientStop { position: Math.min(0.2, 16 / Math.max(1, cardFade.height)); color: "white" }
                        GradientStop { position: Math.max(0.8, 1 - 40 / Math.max(1, cardFade.height)); color: "white" }
                        GradientStop { position: 1; color: cardScroller.atYEnd ? "white" : "transparent" }
                    }
                }
            }

            // File cards: wrap into rows and scroll; the sentence stays pinned.
            Flickable {
                id: cardScroller
                anchors.top: header.bottom
                anchors.topMargin: 12
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: -14
                anchors.rightMargin: -14
                clip: true
                contentWidth: width
                contentHeight: cardFlow.height + 44
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                readonly property bool overflowing: contentHeight > height + 1
                layer.enabled: overflowing
                layer.effect: MultiEffect {
                    maskEnabled: true
                    maskSource: cardFade
                }

                Grid {
                    id: cardFlow
                    x: 14
                    y: 18
                    width: cardScroller.width - 28
                    // Spread the columns across the panel instead of leaving a
                    // ragged gap on the right. Invisible header rows are skipped.
                    readonly property int cardWidth: 118
                    columns: Math.max(1, Math.floor((width + 14) / (cardWidth + 14)))
                    columnSpacing: columns > 1 ? Math.floor((width - columns * cardWidth) / (columns - 1)) : 14
                    rowSpacing: 14

                    Repeater {
                        model: queueModel
                        delegate: DelegateChooser {
                            role: "rowType"
                            DelegateChoice {
                                roleValue: "header"
                                Item { width: 0; height: 0; visible: false }
                            }
                            DelegateChoice {
                                roleValue: "job"
                                FileCard {
                                    removable: !window.running || jobStatus === "queued"
                                    showSelection: window.showSelection
                                    onSelectRequested: {
                                        window.showSelection = true
                                        jobController.selectJob(jobId)
                                    }
                                    onQuickLookRequested: jobController.quickLookSelected()
                                    onRemoveRequested: jobController.removeJob(jobId)
                                }
                            }
                        }
                    }

                    // A quiet tile to add more files without hunting for ⌘O.
                    Rectangle {
                        visible: window.phase === "ready"
                        width: 118
                        height: 148
                        radius: Theme.radiusCard
                        color: addHover.hovered ? Theme.kindTint("image") : "transparent"
                        border.width: 1.5
                        border.color: Theme.kindLine("image")
                        Column {
                            anchors.centerIn: parent
                            spacing: 10
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 40
                                height: 40
                                radius: 20
                                color: Theme.kindTint("image")
                                Image {
                                    anchors.centerIn: parent
                                    width: 20
                                    height: 20
                                    sourceSize: Qt.size(20, 20)
                                    source: "image://icons/plus/" + Theme.hex(Theme.cobaltText) + "/2.5"
                                }
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: window.tr("add_files_card")
                                color: Theme.cobaltText
                                font.family: Theme.font
                                font.pixelSize: 12
                                font.weight: Font.Bold
                            }
                        }
                        HoverHandler { id: addHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: fileDialog.open() }
                        Accessible.role: Accessible.Button
                        Accessible.name: window.tr("add_files_card")
                    }
                }
            }
        }
    }

    // ── sentence words and notices ───────────────────────────────────────

    component Word: Item {
        property alias text: label.text
        property bool strong: false
        width: label.implicitWidth
        height: window.lineHeight
        Text {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            color: parent.strong ? Theme.text : Theme.muted
            font.family: Theme.font
            font.pixelSize: window.sentenceSize
            font.weight: Font.Bold
            font.features: { "tnum": 1 }
        }
    }

    // Skipped or unreadable files: a quiet line, never a toast.
    component NoticeLine: Row {
        property int maxWidth: 600
        readonly property bool intake: jobController.notice.length > 0 && jobController.noticeAction.length === 0
        visible: intake || (jobController.probing && window.phase !== "empty")
        spacing: 8
        Image {
            anchors.verticalCenter: parent.verticalCenter
            width: 15
            height: 15
            sourceSize: Qt.size(15, 15)
            source: "image://icons/info/" + Theme.hex(jobController.noticeKind === "error" && parent.intake ? Theme.error : Theme.muted) + "/2"
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, parent.maxWidth - 60)
            text: parent.intake ? jobController.notice : window.tr("reading_files")
            color: jobController.noticeKind === "error" && parent.intake ? Theme.error : Theme.secondary
            font.family: Theme.font
            font.pixelSize: 13
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Image {
            anchors.verticalCenter: parent.verticalCenter
            visible: parent.intake
            width: 14
            height: 14
            sourceSize: Qt.size(14, 14)
            source: "image://icons/x/" + Theme.hex(Theme.muted) + "/2"
            TapHandler { onTapped: jobController.dismissNotice() }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }
    }

    // ── sheets ───────────────────────────────────────────────────────────

    SettingsSheet {
        id: settingsPanel
        objectName: "settingsPanel"
        onChooseFolderRequested: folderDialog.open()
    }

    ImageOptionsSheet {
        id: imageOptionsPopup
        objectName: "imageOptionsPopup"
    }

    Sheet {
        id: eraseMaskPopup
        objectName: "eraseMaskPopup"
        property string jobId: ""
        property url sourceUrl
        property bool applyGroup: false
        width: Math.min(920, window.width - 64)
        height: Math.min(720, window.height - 64)
        closePolicy: Popup.CloseOnEscape

        function openFor(id, url, group) {
            jobId = id
            sourceUrl = url
            applyGroup = group
            maskCanvas.strokes = []
            brushSlider.value = 34
            open()
            maskCanvas.requestPaint()
        }

        contentItem: ColumnLayout {
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 26
                Layout.rightMargin: 16
                Layout.topMargin: 20
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: window.tr("erase_title")
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 20
                        font.weight: Font.ExtraBold
                    }
                    Text {
                        text: window.tr("erase_hint")
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                    }
                }
                WButton {
                    kind: "ghost"
                    iconName: "x"
                    implicitWidth: 34
                    onClicked: eraseMaskPopup.close()
                    Accessible.name: window.tr("cancel")
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: 26
                Layout.rightMargin: 26
                color: Theme.field
                radius: 18
                clip: true

                Image {
                    id: eraseSourceImage
                    anchors.fill: parent
                    anchors.margins: 12
                    source: eraseMaskPopup.sourceUrl
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: false
                }

                Canvas {
                    id: maskCanvas
                    property var strokes: []
                    x: eraseSourceImage.x + (eraseSourceImage.width - eraseSourceImage.paintedWidth) / 2
                    y: eraseSourceImage.y + (eraseSourceImage.height - eraseSourceImage.paintedHeight) / 2
                    width: eraseSourceImage.paintedWidth
                    height: eraseSourceImage.paintedHeight
                    opacity: 0.58
                    renderTarget: Canvas.Image
                    antialiasing: true

                    onPaint: {
                        var context = getContext("2d")
                        context.reset()
                        context.clearRect(0, 0, width, height)
                        context.strokeStyle = "#FFFFFF"
                        context.fillStyle = "#FFFFFF"
                        context.lineCap = "round"
                        context.lineJoin = "round"
                        for (var strokeIndex = 0; strokeIndex < strokes.length; strokeIndex++) {
                            var stroke = strokes[strokeIndex]
                            var points = stroke.points
                            context.lineWidth = stroke.width
                            if (points.length === 0)
                                continue
                            if (points.length === 1) {
                                context.beginPath()
                                context.arc(points[0].x, points[0].y, stroke.width / 2, 0, Math.PI * 2)
                                context.fill()
                                continue
                            }
                            context.beginPath()
                            context.moveTo(points[0].x, points[0].y)
                            for (var pointIndex = 1; pointIndex < points.length; pointIndex++)
                                context.lineTo(points[pointIndex].x, points[pointIndex].y)
                            context.stroke()
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.CrossCursor
                        onPressed: function(mouse) {
                            var updated = maskCanvas.strokes.slice()
                            updated.push({ "width": brushSlider.value, "points": [{ "x": mouse.x, "y": mouse.y }] })
                            maskCanvas.strokes = updated
                            maskCanvas.requestPaint()
                        }
                        onPositionChanged: function(mouse) {
                            if (!pressed || maskCanvas.strokes.length === 0)
                                return
                            maskCanvas.strokes[maskCanvas.strokes.length - 1].points.push({ "x": mouse.x, "y": mouse.y })
                            maskCanvas.requestPaint()
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 26
                Layout.rightMargin: 26
                Layout.bottomMargin: 20
                spacing: 10
                Text {
                    text: window.tr("brush_size")
                    color: Theme.secondary
                    font.family: Theme.font
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }
                Slider {
                    id: brushSlider
                    Layout.preferredWidth: 180
                    from: 10
                    to: 90
                    value: 34
                    stepSize: 2
                }
                WButton {
                    kind: "ghost"
                    iconName: "retry"
                    text: window.tr("undo")
                    enabled: maskCanvas.strokes.length > 0
                    onClicked: {
                        var updated = maskCanvas.strokes.slice()
                        updated.pop()
                        maskCanvas.strokes = updated
                        maskCanvas.requestPaint()
                    }
                }
                WButton {
                    kind: "ghost"
                    text: window.tr("clear")
                    enabled: maskCanvas.strokes.length > 0
                    onClicked: {
                        maskCanvas.strokes = []
                        maskCanvas.requestPaint()
                    }
                }
                Item { Layout.fillWidth: true }
                WButton {
                    kind: "primary"
                    implicitHeight: 38
                    text: eraseMaskPopup.applyGroup ? window.tr("apply_to_all") : window.tr("apply")
                    enabled: maskCanvas.strokes.length > 0
                    onClicked: {
                        var path = jobController.eraseMaskPath(eraseMaskPopup.jobId)
                        if (path.length > 0 && maskCanvas.save(path)) {
                            jobController.completeEraseMask(eraseMaskPopup.jobId, path, eraseMaskPopup.applyGroup)
                            eraseMaskPopup.close()
                        }
                    }
                }
            }
        }
    }

    DropArea {
        id: dropArea
        anchors.fill: parent
        keys: ["text/uri-list"]
        onDropped: function(drop) {
            if (drop.hasUrls) {
                jobController.addUrls(drop.urls)
                drop.acceptProposedAction()
            }
        }
    }
}
