import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.qmlmodels
import "."

ApplicationWindow {
    id: window
    // Fit comfortably on a 13" MacBook instead of assuming a large display.
    width: Math.max(minimumWidth, Math.min(1240, Math.round(Screen.desktopAvailableWidth * 0.8)))
    height: Math.max(minimumHeight, Math.min(860, Math.round(Screen.desktopAvailableHeight * 0.84)))
    minimumWidth: 860
    minimumHeight: 560
    visible: true
    title: jobController.busy && jobController.progressText.length > 0
        ? "Wemute — " + jobController.progressText
        : "Wemute"
    color: Theme.canvas

    readonly property bool hasPopupOpen: imageOptionsPopup.opened || eraseMaskPopup.opened
        || settingsPanel.opened

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }

    function primaryAction() {
        if (jobController.busy)
            jobController.cancelAll()
        else if (jobController.pendingCount > 0)
            jobController.startAll()
        else if (jobController.succeededCount > 0)
            jobController.revealOutputs()
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
        sequence: "Up"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: jobController.moveSelection(-1)
    }
    Shortcut {
        sequence: "Down"
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: jobController.moveSelection(1)
    }
    Shortcut {
        sequences: ["Ctrl+Return", "Ctrl+Enter"]
        enabled: jobController.hasJobs && !window.hasPopupOpen
        onActivated: window.primaryAction()
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

    // ── menus ────────────────────────────────────────────────────────────

    WMenu {
        id: appMenu
        WMenuItem {
            text: window.tr("auto_start")
            checkable: true
            checked: jobController.autoStart
            onTriggered: jobController.autoStart = checked
        }
        WSeparator { }
        WMenuItem {
            text: window.tr("pause_after_current")
            iconName: "clock"
            visible: jobController.busy
            onTriggered: jobController.pauseAfterCurrent()
        }
        WMenuItem {
            text: window.tr("retry_failed")
            iconName: "retry"
            enabled: jobController.failedCount > 0
            onTriggered: jobController.retryFailed()
        }
        WMenuItem {
            text: window.tr("clear_completed")
            iconName: "check"
            enabled: jobController.succeededCount > 0
            onTriggered: jobController.clearCompleted()
        }
        WMenuItem {
            text: window.tr("clear_all")
            iconName: "trash"
            destructive: true
            enabled: jobController.hasJobs
            onTriggered: jobController.clearAll()
        }
        WSeparator { }
        WMenuItem {
            text: window.tr("nav_settings")
            iconName: "settings"
            shortcutText: "⌘,"
            onTriggered: settingsPanel.openTab("general")
        }
        WMenuItem {
            text: window.tr("about_wemute")
            iconName: "info"
            onTriggered: settingsPanel.openTab("about")
        }
    }

    WMenu {
        id: destinationMenu
        WMenuItem {
            text: window.tr("next_to_original")
            checkable: true
            checked: !jobController.hasCustomDestination
            onTriggered: jobController.resetDestination()
        }
        WMenuItem {
            text: jobController.destinationLabel
            checkable: true
            checked: true
            visible: jobController.hasCustomDestination
        }
        WSeparator { }
        WMenuItem {
            text: window.tr("choose_folder")
            iconName: "folder"
            onTriggered: folderDialog.open()
        }
    }

    WMenu {
        id: rowMenu
        property string jobId: ""
        property string status: ""
        property string mediaKind: ""
        property string name: ""
        function openFor(id, jobStatus, kind, sourceName) {
            jobId = id
            status = jobStatus
            mediaKind = kind
            name = sourceName
            jobController.selectJob(id)
            popup()
        }
        WMenuItem {
            text: window.tr("open_file")
            iconName: "file"
            onTriggered: jobController.openOutput(rowMenu.jobId)
        }
        WMenuItem {
            text: window.tr("reveal")
            iconName: "folder"
            onTriggered: jobController.revealJob(rowMenu.jobId)
        }
        WMenuItem {
            text: window.tr("show_source")
            visible: rowMenu.status === "succeeded"
            onTriggered: jobController.revealSource(rowMenu.jobId)
        }
        WMenuItem {
            text: window.tr("adjust")
            iconName: "settings"
            visible: rowMenu.mediaKind === "image" && rowMenu.status !== "running"
            onTriggered: imageOptionsPopup.openForJob(rowMenu.jobId, rowMenu.name)
        }
        WSeparator { }
        WMenuItem {
            text: window.tr("retry")
            iconName: "retry"
            visible: rowMenu.status === "failed" || rowMenu.status === "cancelled"
            onTriggered: jobController.retryJob(rowMenu.jobId)
        }
        WMenuItem {
            text: window.tr("cancel")
            iconName: "x"
            visible: rowMenu.status === "running" || rowMenu.status === "queued"
            onTriggered: jobController.cancelJob(rowMenu.jobId)
        }
        WMenuItem {
            text: window.tr("remove")
            iconName: "trash"
            destructive: true
            shortcutText: "⌫"
            onTriggered: jobController.removeJob(rowMenu.jobId)
        }
    }

    // ── toolbar ──────────────────────────────────────────────────────────

    Rectangle {
        id: toolbar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Theme.toolbarHeight
        color: Theme.toolbar
        z: 2

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.hairline
        }

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            Image {
                anchors.verticalCenter: parent.verticalCenter
                source: "../assets/brand/wemute-app-icon-1024.png"
                sourceSize: Qt.size(64, 64)
                width: 24
                height: 24
                mipmap: true
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Wemute"
                color: Theme.text
                font.family: Theme.uiFont
                font.pixelSize: 15
                font.weight: Font.Bold
                font.letterSpacing: -0.2
            }
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 1
                height: 14
                color: Theme.border
                visible: jobController.hasJobs
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: jobController.hasJobs
                text: i18n.count("files_summary", jobController.fileCount)
                color: Theme.mutedText
                font.family: Theme.uiFont
                font.pixelSize: 12
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: jobController.probing
                text: window.tr("reading_files")
                color: Theme.cobalt
                font.family: Theme.uiFont
                font.pixelSize: 12
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            WButton {
                kind: "secondary"
                iconName: "plus"
                text: window.tr("add_files")
                height: 30
                onClicked: fileDialog.open()
                ToolTip.visible: hovered
                ToolTip.delay: 700
                ToolTip.text: "⌘O"
            }
            Item { width: 4; height: 1 }
            WButton {
                kind: "ghost"
                iconName: "settings"
                width: 32
                height: 30
                onClicked: settingsPanel.openTab("general")
                Accessible.name: window.tr("nav_settings")
                ToolTip.visible: hovered
                ToolTip.delay: 600
                ToolTip.text: window.tr("nav_settings") + "  ⌘,"
            }
            WButton {
                id: menuButton
                kind: "ghost"
                iconName: "ellipsis"
                width: 32
                height: 30
                onClicked: appMenu.popup(menuButton, menuButton.width - appMenu.width, menuButton.height + 6)
                Accessible.name: "Menu"
            }
        }
    }

    // ── empty state: the drop stage ──────────────────────────────────────

    Item {
        id: dropStage
        anchors.top: toolbar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !jobController.hasJobs
        readonly property bool armed: dropArea.containsDrag || stageHover.hovered

        HoverHandler { id: stageHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: fileDialog.open() }

        Column {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -20
            spacing: 0

            // Two porcelain sheets joined by the cobalt seam — the app icon, alive.
            Item {
                id: mark
                anchors.horizontalCenter: parent.horizontalCenter
                width: 168
                height: 148
                property real spread: dropArea.containsDrag ? 10 : (dropStage.armed ? 4 : 0)
                Behavior on spread { NumberAnimation { duration: 260; easing.type: Easing.OutBack } }

                Rectangle {
                    x: 24 - mark.spread
                    y: 10 - mark.spread
                    width: 78
                    height: 92
                    radius: 14
                    color: Theme.surface
                    border.width: 1
                    border.color: Theme.cardOutline
                    rotation: -4
                    Image {
                        anchors.centerIn: parent
                        width: 24
                        height: 24
                        sourceSize: Qt.size(24, 24)
                        source: "image://icons/file/" + Theme.hex(Theme.subtleText)
                    }
                }
                Rectangle {
                    x: 66 + mark.spread
                    y: 46 + mark.spread
                    width: 78
                    height: 92
                    radius: 14
                    color: Theme.surface
                    border.width: 1
                    border.color: dropArea.containsDrag ? Theme.cobaltLine : Theme.cardOutline
                    rotation: 4
                    Image {
                        anchors.centerIn: parent
                        width: 24
                        height: 24
                        sourceSize: Qt.size(24, 24)
                        source: "image://icons/" + (dropArea.containsDrag ? "download" : "image")
                            + "/" + Theme.hex(dropArea.containsDrag ? Theme.cobalt : Theme.subtleText)
                    }
                }
                Canvas {
                    id: seamCanvas
                    anchors.fill: parent
                    property real glow: dropStage.armed ? 1 : 0.55
                    property color stroke: Theme.cobalt
                    onGlowChanged: requestPaint()
                    onStrokeChanged: requestPaint()
                    Behavior on glow { NumberAnimation { duration: 220 } }
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        ctx.lineCap = "round"
                        ctx.strokeStyle = stroke
                        ctx.globalAlpha = 0.18 * glow
                        ctx.lineWidth = 12
                        ctx.beginPath()
                        ctx.moveTo(98, 52)
                        ctx.bezierCurveTo(78, 60, 92, 92, 70, 100)
                        ctx.stroke()
                        ctx.globalAlpha = 0.55 + 0.45 * glow
                        ctx.lineWidth = 3.5
                        ctx.stroke()
                    }
                }
            }

            Item { width: 1; height: 22 }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: jobController.probing
                    ? window.tr("reading_files")
                    : (dropArea.containsDrag ? window.tr("drop_title_active") : window.tr("drop_title"))
                color: Theme.text
                font.family: Theme.uiFont
                font.pixelSize: 22
                font.weight: Font.DemiBold
                font.letterSpacing: -0.4
            }

            Item { width: 1; height: 8 }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: window.tr("drop_sub")
                color: Theme.mutedText
                font.family: Theme.uiFont
                font.pixelSize: 13
            }

            Item { width: 1; height: 22 }

            Flow {
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(460, dropStage.width - 80)
                spacing: 6
                Repeater {
                    model: ["JPG", "PNG", "HEIC", "WebP", "AVIF", "MP3", "WAV", "FLAC", "M4A", "MP4", "MOV", "MKV", "WebM", "GIF"]
                    Tag { required property string modelData; text: modelData; mono: true }
                }
            }

            Item { width: 1; height: 26 }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 13
                    height: 13
                    sourceSize: Qt.size(13, 13)
                    source: "image://icons/lock/" + Theme.hex(Theme.mutedText)
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: window.tr("drop_hint")
                    color: Theme.mutedText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                }
            }
        }
    }

    // ── queue ────────────────────────────────────────────────────────────

    ListView {
        id: queueView
        anchors.top: toolbar.bottom
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(Theme.contentMaxWidth, parent.width - Theme.pageMargin * 2)
        visible: jobController.hasJobs
        boundsBehavior: Flickable.StopAtBounds
        model: queueModel
        topMargin: 18
        // Room for the floating command bar.
        bottomMargin: commandBar.height + 40
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        delegate: DelegateChooser {
            role: "rowType"

            DelegateChoice {
                roleValue: "header"
                Item {
                    id: header
                    required property int index
                    required property string groupLabel
                    required property string mediaKind
                    required property int groupItemCount
                    required property string targetFormat
                    required property var targetOptions
                    width: queueView.width
                    height: 54 + (index > 0 ? 16 : 0)

                    Rectangle {
                        anchors.fill: parent
                        anchors.topMargin: header.index > 0 ? 16 : 0
                        color: Theme.surface
                        border.width: 1
                        border.color: Theme.cardOutline
                        topLeftRadius: Theme.radiusCard
                        topRightRadius: Theme.radiusCard

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 9

                            Image {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 16
                                height: 16
                                sourceSize: Qt.size(16, 16)
                                source: "image://icons/" + (header.mediaKind === "image" ? "image"
                                    : (header.mediaKind === "audio" ? "music" : "film")) + "/" + Theme.hex(Theme.secondaryText)
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: header.groupLabel
                                color: Theme.text
                                font.family: Theme.uiFont
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: header.groupItemCount
                                color: Theme.mutedText
                                font.family: Theme.monoFont
                                font.features: { "tnum": 1 }
                                font.pixelSize: 12
                            }
                        }

                        // Lines up with the per-file selectors below it.
                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 90 + Math.max(128, Math.min(176, queueView.width * 0.17))
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10
                            visible: header.groupItemCount > 1

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: window.tr("group_all_to")
                                color: Theme.mutedText
                                font.family: Theme.uiFont
                                font.pixelSize: 12
                            }
                            FormatCombo {
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.max(132, Math.min(176, queueView.width * 0.17))
                                height: 30
                                emphasized: true
                                enabled: !jobController.busy
                                model: header.targetOptions || []
                                placeholderText: window.tr("custom")
                                currentIndex: (header.targetOptions || []).indexOf(header.targetFormat)
                                onActivated: jobController.setGroupTargetFormat(header.mediaKind, currentText)
                                Accessible.name: window.tr("group_all_to") + " " + header.groupLabel
                            }
                        }
                    }
                }
            }

            DelegateChoice {
                roleValue: "job"
                JobRow {
                    id: jobDelegate
                    width: queueView.width

                    onSelectRequested: jobController.selectJob(jobId)
                    onOpenRequested: jobController.openOutput(jobId)
                    onRemoveRequested: jobController.removeJob(jobId)
                    onRetryRequested: jobController.retryJob(jobId)
                    onRevealRequested: jobController.revealJob(jobId)
                    onAdjustRequested: {
                        jobController.selectJob(jobId)
                        imageOptionsPopup.openForJob(jobId, sourceName)
                    }
                    onMenuRequested: rowMenu.openFor(jobId, jobStatus, mediaKind, sourceName)
                    onTargetChosen: function(target) { jobController.setTargetFormat(jobId, target) }
                }
            }
        }
    }

    // ── notice ───────────────────────────────────────────────────────────

    Rectangle {
        id: noticeBar
        readonly property bool shown: jobController.notice.length > 0
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: jobController.hasJobs ? commandBar.top : parent.bottom
        anchors.bottomMargin: shown ? 12 : 0
        width: Math.min(parent.width - 48, noticeRow.implicitWidth + 28)
        height: 40
        radius: 12
        color: Theme.dark ? "#2A2F37" : "#1A1D22"
        opacity: shown ? 1 : 0
        visible: opacity > 0
        z: 6

        Behavior on opacity { NumberAnimation { duration: 160 } }
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

        RowLayout {
            id: noticeRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 14
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            Image {
                Layout.preferredWidth: 15
                Layout.preferredHeight: 15
                sourceSize: Qt.size(15, 15)
                source: "image://icons/" + (jobController.noticeKind === "error" ? "circle-x"
                    : (jobController.noticeKind === "success" ? "circle-check" : "info"))
                    + "/" + (jobController.noticeKind === "error" ? "FF8A80"
                        : (jobController.noticeKind === "success" ? "6FD6A3" : "C9CDD4"))
            }
            Text {
                Layout.fillWidth: true
                Layout.maximumWidth: 560
                text: jobController.notice
                color: "#F2F3F5"
                font.family: Theme.uiFont
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            Button {
                id: noticeAction
                visible: jobController.noticeAction.length > 0
                Layout.preferredHeight: 28
                flat: true
                hoverEnabled: true
                onClicked: jobController.runNoticeAction()
                contentItem: Text {
                    text: jobController.noticeAction === "retry" ? window.tr("retry_failed") : window.tr("show_results")
                    color: "#9DB0FF"
                    font.family: Theme.uiFont
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 7
                    color: noticeAction.hovered ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }
            Button {
                id: noticeClose
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                flat: true
                hoverEnabled: true
                onClicked: jobController.dismissNotice()
                Accessible.name: window.tr("dismiss")
                contentItem: Item {
                    Image {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        sourceSize: Qt.size(14, 14)
                        source: "image://icons/x/9AA0AA"
                    }
                }
                background: Rectangle {
                    radius: 7
                    color: noticeClose.hovered ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                }
            }
        }
    }

    // ── floating command bar ─────────────────────────────────────────────

    Rectangle {
        id: commandBar
        visible: jobController.hasJobs
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        width: Math.min(queueView.width, 820)
        height: 60
        radius: 16
        color: Theme.raised
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.shadow
            shadowBlur: 0.9
            shadowVerticalOffset: 6
            shadowOpacity: Theme.dark ? 0.9 : 0.55
        }
        border.width: 1
        border.color: Theme.border
        z: 5


        // Overall progress traces the bar's lower edge, like the icon's seam.
        Item {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            height: 2
            visible: jobController.busy
            Rectangle {
                height: 2
                radius: 1
                width: parent.width * jobController.overallProgress
                color: Theme.cobalt
                Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 6

            Button {
                id: destinationButton
                Layout.preferredHeight: 38
                Layout.maximumWidth: 260
                hoverEnabled: true
                onClicked: destinationMenu.popup(destinationButton, 0, -destinationMenu.implicitHeight - 8)
                Accessible.name: window.tr("save_to")
                leftPadding: 10
                rightPadding: 10

                HoverHandler { cursorShape: Qt.PointingHandCursor }

                contentItem: RowLayout {
                    spacing: 9
                    Image {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        sourceSize: Qt.size(16, 16)
                        source: "image://icons/folder/" + Theme.hex(Theme.secondaryText)
                    }
                    ColumnLayout {
                        spacing: 0
                        Text {
                            text: window.tr("save_to")
                            color: Theme.mutedText
                            font.family: Theme.uiFont
                            font.pixelSize: 11
                        }
                        Text {
                            Layout.maximumWidth: 170
                            text: jobController.hasCustomDestination
                                ? jobController.destinationLabel
                                : window.tr("next_to_original")
                            color: Theme.text
                            font.family: Theme.uiFont
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            elide: Text.ElideMiddle
                        }
                    }
                    Image {
                        Layout.preferredWidth: 12
                        Layout.preferredHeight: 12
                        sourceSize: Qt.size(12, 12)
                        source: "image://icons/chevron-down/" + Theme.hex(Theme.mutedText)
                    }
                }
                background: Rectangle {
                    radius: 10
                    color: destinationButton.down ? Theme.pressFill : (destinationButton.hovered ? Theme.hoverFill : "transparent")
                }
            }

            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 22
                color: Theme.hairline
                visible: imageOptionsButton.visible
            }

            WButton {
                id: imageOptionsButton
                kind: "ghost"
                iconName: "settings"
                text: window.tr("image_options")
                visible: jobController.hasImageJobs
                enabled: !jobController.busy
                onClicked: imageOptionsPopup.openBatch()
            }

            Item { Layout.fillWidth: true }

            Text {
                text: jobController.busy
                    ? jobController.progressText
                    : (jobController.pendingCount > 0
                        ? i18n.count("summary_ready", jobController.pendingCount)
                        : (jobController.succeededCount > 0 ? window.tr("summary_done") : ""))
                color: jobController.busy ? Theme.cobalt : Theme.mutedText
                font.family: Theme.uiFont
                font.pixelSize: 12
                font.weight: jobController.busy ? Font.Medium : Font.Normal
            }

            WButton {
                id: primaryButton
                Layout.preferredHeight: 40
                Layout.minimumWidth: 132
                fontSize: 14
                kind: jobController.busy ? "secondary" : "primary"
                iconName: jobController.busy
                    ? "x"
                    : (jobController.pendingCount > 0 ? "arrow-right" : "folder")
                text: jobController.busy
                    ? window.tr("stop")
                    : (jobController.pendingCount > 0
                        ? (jobController.pendingCount === jobController.fileCount
                            ? window.tr("convert_all")
                            : i18n.count("convert_count", jobController.pendingCount))
                        : (jobController.succeededCount > 0 ? window.tr("show_results") : window.tr("convert_all")))
                enabled: jobController.hasJobs
                    && (jobController.busy || jobController.pendingCount > 0 || jobController.succeededCount > 0)
                onClicked: window.primaryAction()
                ToolTip.visible: hovered
                ToolTip.delay: 800
                ToolTip.text: "⌘↩"
            }
        }
    }

    // ── panels and editors ───────────────────────────────────────────────

    SettingsPanel {
        id: settingsPanel
        objectName: "settingsPanel"
        onChooseFolderRequested: folderDialog.open()
    }

    Popup {
        id: imageOptionsPopup
        objectName: "imageOptionsPopup"
        property string jobId: ""
        property string displayName: ""
        parent: Overlay.overlay
        x: Math.max(12, Math.min(parent.width - width - 12, commandBar.x + imageOptionsButton.x))
        y: commandBar.y - height - 10
        width: 360
        padding: 0
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        function syncControls() {
            var single = jobId.length > 0
            resizeControl.currentIndex = resizeControl.presetKeys.indexOf(
                single ? jobController.imageResizePresetFor(jobId) : jobController.imageResizePreset)
            qualityControl.current = single ? jobController.imageQualityPresetFor(jobId) : jobController.imageQualityPreset
            cornerControl.current = single ? jobController.imageCornerPresetFor(jobId) : jobController.imageCornerPreset
            var targetSize = single ? jobController.imageTargetSizeKbFor(jobId) : jobController.imageTargetSizeKb
            targetSizeField.text = targetSize > 0 ? String(targetSize) : ""
        }
        function openBatch() {
            jobId = ""
            displayName = window.tr("all_images")
            syncControls()
            open()
        }
        function openForJob(id, name) {
            jobId = id
            displayName = name
            syncControls()
            open()
        }

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
            NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: 160; easing.type: Easing.OutCubic }
        }

        background: Rectangle {
            color: Theme.raised
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Theme.shadow
                shadowBlur: 0.9
                shadowVerticalOffset: 6
                shadowOpacity: Theme.dark ? 0.9 : 0.55
            }
            radius: Theme.radiusCard
            border.width: 1
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.topMargin: 14
                spacing: 2
                Text {
                    text: window.tr("image_options")
                    color: Theme.text
                    font.family: Theme.uiFont
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
                Text {
                    Layout.fillWidth: true
                    text: imageOptionsPopup.displayName
                    color: Theme.mutedText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                    elide: Text.ElideMiddle
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: 16
                columns: 2
                columnSpacing: 14
                rowSpacing: 10

                Text {
                    text: window.tr("resize")
                    color: Theme.secondaryText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                }
                FormatCombo {
                    id: resizeControl
                    Layout.fillWidth: true
                    height: 30
                    property var presetKeys: ["original", "half", "edge2048", "edge1080"]
                    model: [window.tr("original_size"), window.tr("half_size"), window.tr("long_edge_2048"), window.tr("long_edge_1080")]
                    placeholderText: window.tr("custom")
                    onActivated: function(index) {
                        if (imageOptionsPopup.jobId.length > 0)
                            jobController.setJobImageResizePreset(imageOptionsPopup.jobId, presetKeys[index])
                        else
                            jobController.setImageResizePreset(presetKeys[index])
                    }
                }

                Text {
                    text: window.tr("quality")
                    color: Theme.secondaryText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                }
                Segmented {
                    id: qualityControl
                    Layout.fillWidth: true
                    stretch: true
                    options: [
                        { "key": "small", "label": window.tr("smaller") },
                        { "key": "balanced", "label": window.tr("balanced") },
                        { "key": "best", "label": window.tr("best_quality") }
                    ]
                    onActivated: function(key) {
                        current = key
                        if (imageOptionsPopup.jobId.length > 0)
                            jobController.setJobImageQualityPreset(imageOptionsPopup.jobId, key)
                        else
                            jobController.setImageQualityPreset(key)
                    }
                }

                Text {
                    text: window.tr("corners")
                    color: Theme.secondaryText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                }
                Segmented {
                    id: cornerControl
                    Layout.fillWidth: true
                    stretch: true
                    options: [
                        { "key": "none", "label": window.tr("none") },
                        { "key": "soft", "label": window.tr("soft_corners") },
                        { "key": "round", "label": window.tr("round_corners") }
                    ]
                    onActivated: function(key) {
                        current = key
                        if (imageOptionsPopup.jobId.length > 0)
                            jobController.setJobImageCornerPreset(imageOptionsPopup.jobId, key)
                        else
                            jobController.setImageCornerPreset(key)
                    }
                }

                Text {
                    text: window.tr("target_size")
                    color: Theme.secondaryText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                }
                TextField {
                    id: targetSizeField
                    Layout.fillWidth: true
                    implicitHeight: 30
                    placeholderText: window.tr("off")
                    placeholderTextColor: Theme.subtleText
                    color: Theme.text
                    font.family: Theme.monoFont
                    font.features: { "tnum": 1 }
                    font.pixelSize: 12
                    leftPadding: 11
                    rightPadding: 40
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 0; top: 1000000 }
                    onEditingFinished: {
                        var value = text.length > 0 ? parseInt(text) : 0
                        if (imageOptionsPopup.jobId.length > 0)
                            jobController.setJobImageTargetSizeKb(imageOptionsPopup.jobId, value)
                        else
                            jobController.setImageTargetSizeKb(value)
                    }
                    background: Rectangle {
                        color: Theme.surface
                        radius: Theme.radiusControl
                        border.width: targetSizeField.activeFocus ? 2 : 1
                        border.color: targetSizeField.activeFocus ? Theme.cobaltLine : Theme.border
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 11
                        anchors.verticalCenter: parent.verticalCenter
                        text: window.tr("kb")
                        color: Theme.mutedText
                        font.family: Theme.monoFont
                        font.features: { "tnum": 1 }
                        font.pixelSize: 12
                    }
                }
                Item { width: 1; height: 1 }
                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: -4
                    text: window.tr("target_size_hint")
                    color: Theme.mutedText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    Popup {
        id: eraseMaskPopup
        objectName: "eraseMaskPopup"
        property string jobId: ""
        property url sourceUrl
        property bool applyGroup: false
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(920, window.width - 64)
        height: Math.min(720, window.height - 64)
        padding: 0
        modal: true
        focus: true
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

        Overlay.modal: Rectangle { color: Theme.scrim }

        background: Rectangle {
            color: Theme.raised
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
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 12
                Layout.topMargin: 16
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: window.tr("erase_title")
                        color: Theme.text
                        font.family: Theme.uiFont
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: window.tr("erase_hint")
                        color: Theme.mutedText
                        font.family: Theme.uiFont
                        font.pixelSize: 12
                    }
                }
                WButton {
                    kind: "ghost"
                    iconName: "x"
                    width: 30
                    height: 30
                    onClicked: eraseMaskPopup.close()
                    Accessible.name: window.tr("cancel")
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                color: Theme.sunken
                radius: 12
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
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.bottomMargin: 16
                spacing: 10
                Text {
                    text: window.tr("brush_size")
                    color: Theme.secondaryText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
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
                    height: 36
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

        // With a queue on screen, show a quiet cobalt frame instead of a wash.
        Rectangle {
            anchors.fill: parent
            anchors.margins: 6
            radius: 14
            color: Theme.cobaltSoft
            border.width: 2
            border.color: Theme.cobaltLine
            opacity: parent.containsDrag && jobController.hasJobs ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 120 } }

            Rectangle {
                anchors.centerIn: parent
                width: dropLabel.implicitWidth + 32
                height: 40
                radius: 12
                color: Theme.cobalt
                Text {
                    id: dropLabel
                    anchors.centerIn: parent
                    text: window.tr("drop_title_active")
                    color: "#FFFFFF"
                    font.family: Theme.uiFont
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
            }
        }
    }
}
