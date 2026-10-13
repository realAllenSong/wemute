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
    // The sentence gets smaller as more kinds share it.
    readonly property int groupLines: jobController.groups.length
    readonly property int sentenceSize: (glass.width < 820 ? 26 : 30)
        - (groupLines >= 4 ? 6 : (groupLines === 3 ? 3 : 0))
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
        // ⌘⌫ on macOS.
        sequence: "Ctrl+Backspace"
        enabled: window.phase === "ready" && !window.hasPopupOpen
        onActivated: jobController.clearWithUndo()
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

                    // Many kinds at once: the lines scroll instead of pushing the cards away.
                    Flickable {
                        id: linesScroller
                        width: sentence.width
                        // Stop at a line boundary so no sentence is ever cut in half.
                        readonly property real maxHeight: Math.max(window.lineHeight * 2, glassFrame.height * 0.42)
                        readonly property real wholeLinesHeight: {
                            let total = 0
                            for (let index = 0; index < linesColumn.children.length; ++index) {
                                const line = linesColumn.children[index]
                                if (!line.visible || line.height <= 0)
                                    continue
                                if (total + line.height > maxHeight)
                                    break
                                total += line.height
                            }
                            return total > 0 ? total : maxHeight
                        }
                        height: Math.min(contentHeight, wholeLinesHeight)
                        contentWidth: width
                        contentHeight: linesColumn.height
                        interactive: contentHeight > height + 1
                        boundsBehavior: Flickable.StopAtBounds
                        clip: interactive
                        ScrollBar.vertical: ScrollBar { policy: linesScroller.interactive ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff }

                        Column {
                            id: linesColumn
                            width: linesScroller.width - (linesScroller.interactive ? 14 : 0)
                            spacing: 0

                            Repeater {
                                model: jobController.groups

                                Column {
                                    id: line
                                    required property var modelData
                                    width: linesColumn.width
                                    spacing: 0
                                    HoverHandler { id: lineHover }

                                    Flow {
                                        width: line.width
                                        spacing: 12

                                        Word { text: line.modelData.lead }
                                        Word { text: line.modelData.countLabel; strong: true }
                                        Word { text: line.modelData.verb }
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
                                                text: line.modelData.target.length > 0 ? line.modelData.targetLabel : window.tr("mixed_formats")
                                                onClicked: formatMenu.open()
                                                Accessible.name: line.modelData.countLabel + " → " + text
                                                PillMenu {
                                                    id: formatMenu
                                                    objectName: "formatMenu-" + line.modelData.kind
                                                    onOpened: window.openMenus++
                                                    onClosed: window.openMenus--
                                                    entries: {
                                                        var list = line.modelData.entries.slice()
                                                        if (line.modelData.kind === "image") {
                                                            // Image options belong to the formats, so they close
                                                            // that section when the menu has several.
                                                            var at = list.length
                                                            var headers = 0
                                                            for (var i = 0; i < list.length; i++) {
                                                                if (list[i].columnBreak === true
                                                                        || ((list[i].header || "").length > 0 && ++headers === 2)) {
                                                                    at = i
                                                                    break
                                                                }
                                                            }
                                                            list.splice(at, 0, { "separator": true },
                                                                { "key": "__options", "label": window.tr("more_options"), "icon": "settings" })
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
                                        // × on hover removes this whole kind from the batch.
                                        Item {
                                            width: 26
                                            height: window.lineHeight
                                            visible: window.phase === "ready"
                                            Rectangle {
                                                id: removeKindButton
                                                anchors.verticalCenter: parent.verticalCenter
                                                width: 26
                                                height: 26
                                                radius: 13
                                                color: removeKindHover.hovered ? Theme.error : (Theme.dark ? "#3A4360" : "#182033")
                                                opacity: lineHover.hovered || removeKindButton.activeFocus ? 1 : 0
                                                Behavior on opacity { NumberAnimation { duration: 120 } }
                                                Image {
                                                    anchors.centerIn: parent
                                                    width: 11
                                                    height: 11
                                                    sourceSize: Qt.size(11, 11)
                                                    source: "image://icons/x/ffffff/3.5"
                                                }
                                                HoverHandler { id: removeKindHover; cursorShape: Qt.PointingHandCursor }
                                                TapHandler { onTapped: jobController.removeKind(line.modelData.kind) }
                                                Accessible.role: Accessible.Button
                                                Accessible.name: window.tr("remove_kind") + " " + line.modelData.countLabel
                                            }
                                        }
                                    }

                                    ComponentLine {
                                        group: line.modelData
                                        width: line.width
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
                            anchors.right: clearButton.visible ? clearButton.left : actionButton.left
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
                            id: clearButton
                            anchors.right: actionButton.left
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            visible: window.phase === "ready"
                            kind: "quiet"
                            text: window.tr("clear_list")
                            onClicked: jobController.clearWithUndo()
                            ToolTip.visible: hovered
                            ToolTip.delay: 800
                            ToolTip.text: "⌘⌫"
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
                            // Some converters cannot measure progress; a sweep shows they are working.
                            Item {
                                anchors.fill: parent
                                anchors.leftMargin: 5
                                anchors.rightMargin: 5
                                clip: true
                                visible: jobController.anyIndeterminate
                                Rectangle {
                                    id: meterSweep
                                    width: parent.width * 0.22
                                    height: parent.height
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop { position: 0; color: Qt.rgba(111 / 255, 168 / 255, 1, 0) }
                                        GradientStop { position: 0.5; color: Qt.rgba(111 / 255, 168 / 255, 1, Theme.dark ? 0.55 : 0.45) }
                                        GradientStop { position: 1; color: Qt.rgba(111 / 255, 168 / 255, 1, 0) }
                                    }
                                    NumberAnimation on x {
                                        running: jobController.anyIndeterminate && window.running
                                        loops: Animation.Infinite
                                        from: -meterSweep.width
                                        to: meterSweep.parent.width
                                        duration: 1600
                                        easing.type: Easing.InOutSine
                                    }
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
        visible: label.text.length > 0
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
        readonly property bool undo: jobController.noticeAction === "undo"
        readonly property bool intake: jobController.notice.length > 0
            && (jobController.noticeAction.length === 0 || undo)
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
            width: Math.min(implicitWidth, parent.maxWidth - (parent.undo ? 120 : 60))
            text: parent.intake ? jobController.notice : window.tr("reading_files")
            color: jobController.noticeKind === "error" && parent.intake ? Theme.error : Theme.secondary
            font.family: Theme.font
            font.pixelSize: 13
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: parent.undo
            text: window.tr("undo")
            color: Theme.cobaltText
            font.family: Theme.font
            font.pixelSize: 13
            font.weight: Font.Bold
            TapHandler { onTapped: jobController.undoClear() }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
            Accessible.role: Accessible.Button
            Accessible.name: text
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

    // Under a sentence line whose files need a component first:
    // "需要先下载文档组件 · 300 MB  下载", then its progress.
    component ComponentLine: Item {
        id: componentLine
        property var group: ({})
        readonly property string phase: group.component ? group.componentState : ""
        readonly property bool busy: phase === "downloading" || phase === "installing" || phase === "queued"
        readonly property color tone: phase === "failed" ? Theme.error : Theme.kindColor(group.kind || "neutral")
        function fill(key) {
            return window.tr(key)
                .replace("{name}", group.componentName || "")
                .replace("{size}", group.componentSize || "")
                .replace("{percent}", Math.floor((group.componentProgress || 0) * 100))
        }
        visible: phase.length > 0
        width: parent ? parent.width : 0
        height: visible ? 36 : 0

        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            Image {
                anchors.verticalCenter: parent.verticalCenter
                width: 16
                height: 16
                sourceSize: Qt.size(16, 16)
                source: "image://icons/" + (componentLine.phase === "failed" ? "info" : "download")
                    + "/" + Theme.hex(componentLine.tone) + "/2.2"
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: componentLine.fill({
                    "missing": "component_needed",
                    "queued": "component_queued",
                    "downloading": "component_downloading",
                    "installing": "component_installing",
                    "failed": "component_failed"
                }[componentLine.phase] || "component_needed")
                color: componentLine.phase === "failed" ? Theme.error : Theme.secondary
                font.family: Theme.font
                font.pixelSize: 15
                font.weight: Font.DemiBold
                font.features: { "tnum": 1 }
            }
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                visible: componentLine.busy
                width: 120
                height: 5
                radius: 2.5
                color: Theme.track
                clip: true
                Rectangle {
                    visible: componentLine.phase === "downloading"
                    height: parent.height
                    radius: 2.5
                    width: Math.max(height, parent.width * (componentLine.group.componentProgress || 0))
                    color: componentLine.tone
                    Behavior on width { NumberAnimation { duration: 200 } }
                }
                Rectangle {
                    id: componentSweep
                    visible: componentLine.phase !== "downloading"
                    width: parent.width * 0.35
                    height: parent.height
                    radius: 2.5
                    color: componentLine.tone
                    NumberAnimation on x {
                        running: componentLine.busy && componentLine.phase !== "downloading"
                        loops: Animation.Infinite
                        from: -componentSweep.width
                        to: 120
                        duration: 1300
                        easing.type: Easing.InOutQuad
                    }
                }
            }
            Text {
                id: componentAction
                anchors.verticalCenter: parent.verticalCenter
                visible: componentLine.phase !== "installing"
                text: componentLine.busy ? window.tr("cancel")
                    : (componentLine.phase === "failed" ? window.tr("retry")
                        : (componentLine.group.componentResumable ? window.tr("resume") : window.tr("component_get")))
                color: componentLine.busy ? Theme.secondary : Theme.cobaltText
                font.family: Theme.font
                font.pixelSize: 15
                font.weight: Font.Bold
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: componentLine.busy
                        ? jobController.cancelComponent(componentLine.group.component)
                        : jobController.installComponent(componentLine.group.component)
                }
                Accessible.role: Accessible.Button
                Accessible.name: text
            }
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

    EraseEditor { id: eraseMaskPopup; objectName: "eraseMaskPopup" }

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
