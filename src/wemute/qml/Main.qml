import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: window
    width: 1440
    height: 1024
    minimumWidth: 960
    minimumHeight: 640
    visible: true
    title: "Wemute"
    color: Theme.window

    Shortcut {
        sequences: [StandardKey.Open]
        onActivated: fileDialog.open()
    }
    Shortcut {
        sequences: [StandardKey.Paste]
        onActivated: jobController.pasteFiles()
    }
    Shortcut {
        sequence: "Space"
        enabled: jobController.hasJobs
        onActivated: jobController.quickLookSelected()
    }

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }

    FileDialog {
        id: fileDialog
        title: window.tr("choose_files")
        fileMode: FileDialog.OpenFiles
        onAccepted: jobController.addUrls(selectedFiles)
    }

    FolderDialog {
        id: folderDialog
        title: window.tr("same_folder")
        onAccepted: jobController.setDestination(selectedFolder.toString())
    }

    Menu {
        id: appMenu
        MenuItem {
            text: window.tr("pause_after_current")
            visible: jobController.busy
            onTriggered: jobController.pauseAfterCurrent()
        }
        MenuSeparator { visible: jobController.busy }
        MenuItem {
            text: window.tr("retry_failed")
            onTriggered: jobController.retryFailed()
        }
        MenuSeparator { }
        MenuItem {
            text: window.tr("clear_completed")
            onTriggered: jobController.clearCompleted()
        }
        MenuItem {
            text: window.tr("clear_all")
            onTriggered: jobController.clearAll()
        }
        MenuSeparator { }
        MenuItem {
            text: window.tr("about_wemute")
            onTriggered: aboutPopup.open()
        }
    }

    Popup {
        id: imageOptionsPopup
        objectName: "imageOptionsPopup"
        parent: Overlay.overlay
        x: Theme.pageMargin + 196
        y: window.height - bottomBar.height - height - 12
        width: 380
        height: 250
        padding: 0
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#22272C"
            border.width: 1
            border.color: Theme.border
            radius: 12
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10

            Text {
                text: window.tr("image_options")
                color: Theme.text
                font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                font.pixelSize: 16
                font.weight: Font.Medium
                Layout.bottomMargin: 2
            }

            RowLayout {
                spacing: 14
                Text {
                    text: window.tr("resize")
                    color: Theme.secondaryText
                    font.pixelSize: 14
                    Layout.preferredWidth: 82
                }
                FormatCombo {
                    Layout.fillWidth: true
                    height: 42
                    model: [
                        window.tr("original_size"),
                        window.tr("half_size"),
                        window.tr("long_edge_2048"),
                        window.tr("long_edge_1080")
                    ]
                    property var presetKeys: ["original", "half", "edge2048", "edge1080"]
                    currentIndex: presetKeys.indexOf(jobController.imageResizePreset)
                    placeholderText: window.tr("custom")
                    onActivated: jobController.setImageResizePreset(presetKeys[index])
                }
            }

            RowLayout {
                spacing: 14
                Text {
                    text: window.tr("quality")
                    color: Theme.secondaryText
                    font.pixelSize: 14
                    Layout.preferredWidth: 82
                }
                FormatCombo {
                    Layout.fillWidth: true
                    height: 42
                    model: [window.tr("smaller"), window.tr("balanced"), window.tr("best_quality")]
                    property var presetKeys: ["small", "balanced", "best"]
                    currentIndex: presetKeys.indexOf(jobController.imageQualityPreset)
                    placeholderText: window.tr("custom")
                    onActivated: jobController.setImageQualityPreset(presetKeys[index])
                }
            }

            RowLayout {
                spacing: 14
                Text {
                    text: window.tr("corners")
                    color: Theme.secondaryText
                    font.pixelSize: 14
                    Layout.preferredWidth: 82
                }
                FormatCombo {
                    Layout.fillWidth: true
                    height: 42
                    model: [window.tr("none"), window.tr("soft_corners"), window.tr("round_corners")]
                    property var presetKeys: ["none", "soft", "round"]
                    currentIndex: presetKeys.indexOf(jobController.imageCornerPreset)
                    placeholderText: window.tr("custom")
                    onActivated: jobController.setImageCornerPreset(presetKeys[index])
                }
            }
        }
    }

    Popup {
        id: aiToolsPopup
        objectName: "aiToolsPopup"
        parent: Overlay.overlay
        x: Theme.pageMargin + 340
        y: window.height - bottomBar.height - height - 12
        width: 460
        height: 244
        padding: 0
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#22272C"
            border.width: 1
            border.color: Theme.border
            radius: 12
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 8

            Text {
                text: window.tr("on_device_ai")
                color: Theme.text
                font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                font.pixelSize: 16
                font.weight: Font.Medium
            }

            Text {
                text: window.tr("ai_local_hint")
                color: Theme.secondaryText
                font.pixelSize: 13
                Layout.bottomMargin: 6
            }

            Repeater {
                model: aiModelController.catalog

                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 126
                    radius: 10
                    color: Theme.surface
                    border.width: 1
                    border.color: Theme.border

                    Text {
                        id: modelName
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: 14
                        anchors.topMargin: 13
                        text: parent.modelData.name
                        color: Theme.text
                        font.pixelSize: 14
                        font.weight: Font.Medium
                    }

                    Text {
                        anchors.left: modelName.left
                        anchors.top: modelName.bottom
                        anchors.topMargin: 5
                        text: parent.modelData.sizeLabel + "  ·  " + parent.modelData.license
                        color: Theme.secondaryText
                        font.pixelSize: 12
                    }

                    Text {
                        anchors.left: modelName.left
                        anchors.right: modelAction.left
                        anchors.rightMargin: 18
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 14
                        text: parent.modelData.installed
                            ? window.tr("model_ready")
                            : parent.modelData.description
                        color: Theme.tertiaryText
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }

                    WButton {
                        id: modelAction
                        anchors.right: parent.right
                        anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        width: 92
                        height: 36
                        quiet: parent.modelData.installed
                        text: parent.modelData.installing
                            ? window.tr("cancel")
                            : (parent.modelData.installed
                                ? window.tr("remove_model")
                                : window.tr("get_model"))
                        onClicked: {
                            if (parent.modelData.installing) {
                                aiModelController.cancelInstall()
                            } else if (parent.modelData.installed) {
                                aiModelController.removePackage(parent.modelData.id)
                            } else {
                                aiModelController.installPackage(parent.modelData.id)
                            }
                        }
                    }

                    Item {
                        anchors.left: modelName.left
                        anchors.right: modelAction.left
                        anchors.rightMargin: 18
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 16
                        height: 3
                        visible: parent.modelData.installing

                        Rectangle {
                            anchors.fill: parent
                            radius: 2
                            color: Theme.border
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: parent.width * parent.parent.modelData.progress
                            radius: 2
                            color: Theme.accent
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: aiModelController.lastError
                color: Theme.error
                font.pixelSize: 11
                elide: Text.ElideRight
                visible: text.length > 0
            }
        }
    }

    Popup {
        id: aboutPopup
        objectName: "aboutPopup"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(560, window.width - 48)
        height: Math.min(630, window.height - 56)
        padding: 0
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#202529"
            border.width: 1
            border.color: Theme.border
            radius: 16
        }

        Overlay.modal: Rectangle { color: "#B3000000" }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                spacing: 18

                Image {
                    source: "../assets/brand/wemute-app-icon-1024.png"
                    sourceSize: Qt.size(82, 82)
                    Layout.preferredWidth: 82
                    Layout.preferredHeight: 82
                    mipmap: true
                    smooth: true
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text {
                        text: "Wemute"
                        color: Theme.text
                        font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                        font.pixelSize: 27
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: window.tr("about_tagline")
                        color: Theme.secondaryText
                        font.pixelSize: 14
                    }
                    Text {
                        text: window.tr("version") + " " + appInfoController.version
                        color: Theme.tertiaryText
                        font.pixelSize: 12
                    }
                }

                WButton {
                    width: 34
                    height: 34
                    quiet: true
                    text: "×"
                    onClicked: aboutPopup.close()
                    Accessible.name: window.tr("cancel")
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 22
                Layout.bottomMargin: 22
                text: window.tr("privacy_note")
                color: Theme.secondaryText
                font.pixelSize: 13
                wrapMode: Text.WordWrap
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.divider
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 20
                Layout.bottomMargin: 12
                text: window.tr("third_party")
                color: Theme.text
                font.pixelSize: 15
                font.weight: Font.Medium
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                Column {
                    width: parent.width

                    Repeater {
                        model: appInfoController.thirdParty

                        Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 65
                            color: Theme.transparent

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                color: Theme.divider
                            }

                            Text {
                                id: componentName
                                anchors.left: parent.left
                                anchors.right: licenseButton.left
                                anchors.rightMargin: 12
                                anchors.top: parent.top
                                anchors.topMargin: 11
                                text: parent.modelData.name + "  " + parent.modelData.version
                                color: Theme.text
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.right: licenseButton.left
                                anchors.rightMargin: 12
                                anchors.top: componentName.bottom
                                anchors.topMargin: 6
                                text: parent.modelData.license
                                color: Theme.tertiaryText
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }

                            WButton {
                                id: licenseButton
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: 78
                                height: 32
                                quiet: true
                                text: window.tr("view_license")
                                onClicked: appInfoController.openUrl(parent.modelData.url)
                            }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 14
                text: window.tr("about_copyright")
                horizontalAlignment: Text.AlignHCenter
                color: Theme.tertiaryText
                font.pixelSize: 11
            }
        }
    }

    Rectangle {
        id: topRule
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: Theme.divider
    }

    Item {
        id: topBar
        anchors.top: topRule.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 70

        Text {
            anchors.left: parent.left
            anchors.leftMargin: Theme.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            text: i18n.count("files", jobController.fileCount)
            color: Theme.secondaryText
            font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
            font.pixelSize: 17
            font.weight: Font.Medium
            visible: jobController.hasJobs
        }

        WButton {
            id: addFilesButton
            anchors.right: menuButton.left
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            height: 38
            width: 94
            quiet: true
            text: window.tr("add_files")
            onClicked: fileDialog.open()
            Accessible.name: text
        }

        Button {
            id: menuButton
            anchors.right: parent.right
            anchors.rightMargin: Theme.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            width: 38
            height: 38
            hoverEnabled: true
            onClicked: appMenu.popup(menuButton, 0, menuButton.height + 4)
            Accessible.name: "Menu"

            contentItem: Image {
                source: "image://icons/menu"
                sourceSize: Qt.size(18, 18)
                width: 18
                height: 18
                anchors.centerIn: parent
                opacity: 0.84
            }

            background: Rectangle {
                radius: 19
                color: menuButton.hovered ? Theme.surfaceHover : Theme.transparent
                border.width: menuButton.hovered ? 1 : 0
                border.color: Theme.border
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.leftMargin: Theme.pageMargin
        anchors.rightMargin: Theme.pageMargin
        height: 1
        color: Theme.divider
        visible: jobController.hasJobs
    }

    ListView {
        id: queueView
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.pageMargin
        anchors.rightMargin: Theme.pageMargin
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: queueModel
        visible: jobController.hasJobs
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        property real fittedRowHeight: Math.max(
            96,
            Math.min(
                Theme.rowHeight,
                (height - jobController.groupCount * Theme.headerHeight)
                    / Math.max(1, jobController.fileCount)
            )
        )

        delegate: Item {
            id: delegateRoot
            required property string rowType
            required property string jobId
            required property string groupLabel
            required property string sourceName
            required property string sourcePath
            required property string metadata
            required property string thumbnailUrl
            required property string targetFormat
            required property var targetOptions
            required property string jobStatus
            required property string statusTitle
            required property string statusSubtitle
            required property real jobProgress
            required property bool rowSelected
            required property bool canConvert
            required property string mediaKind
            required property int groupItemCount

            width: queueView.width
            height: rowType === "header" ? Theme.headerHeight : queueView.fittedRowHeight

            Item {
                anchors.fill: parent
                visible: delegateRoot.rowType === "header"

                Text {
                    id: groupTitle
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 13
                    text: delegateRoot.groupLabel
                    color: Theme.secondaryText
                    font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                    font.pixelSize: 16
                    font.weight: Font.Medium
                }

                Text {
                    anchors.left: groupTitle.right
                    anchors.leftMargin: 10
                    anchors.verticalCenter: groupTitle.verticalCenter
                    text: delegateRoot.groupItemCount
                    color: Theme.tertiaryText
                    font.pixelSize: 13
                    visible: delegateRoot.groupItemCount > 1
                }

                FormatCombo {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 7
                    width: 210
                    height: 38
                    visible: delegateRoot.groupItemCount > 1
                    enabled: !jobController.busy
                    model: delegateRoot.targetOptions || []
                    prefixText: window.tr("all_to")
                    placeholderText: window.tr("custom")
                    currentIndex: (delegateRoot.targetOptions || []).indexOf(delegateRoot.targetFormat)
                    onActivated: jobController.setGroupTargetFormat(delegateRoot.mediaKind, currentText)
                    Accessible.name: window.tr("all_to") + delegateRoot.groupLabel
                }
            }

            Item {
                id: jobRow
                anchors.fill: parent
                visible: delegateRoot.rowType === "job"

                HoverHandler { id: rowHover }
                TapHandler {
                    acceptedButtons: Qt.LeftButton
                    onTapped: jobController.selectJob(delegateRoot.jobId)
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: -10
                    anchors.rightMargin: -10
                    radius: 11
                    color: delegateRoot.rowSelected
                        ? Theme.surfaceSelected
                        : (rowHover.hovered ? Theme.surfaceHover : Theme.transparent)
                    opacity: delegateRoot.rowSelected ? 0.92 : 0.72
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Theme.divider
                }

                Rectangle {
                    id: thumbFrame
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    height: Math.min(98, parent.height - 18)
                    width: height * 1.42
                    radius: 9
                    color: Theme.surface
                    border.width: 1
                    border.color: Theme.border
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 1
                        source: delegateRoot.thumbnailUrl
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: false
                        sourceSize: Qt.size(244, 172)
                    }
                }

                Item {
                    id: sourceInfo
                    anchors.left: thumbFrame.right
                    anchors.leftMargin: 24
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(250, parent.width * 0.27)
                    height: 58

                    Text {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        text: delegateRoot.sourceName
                        color: Theme.text
                        font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                        font.pixelSize: 17
                        font.weight: Font.Medium
                        elide: Text.ElideMiddle
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        text: delegateRoot.metadata
                        color: Theme.secondaryText
                        font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }

                Image {
                    id: directionIcon
                    anchors.left: sourceInfo.right
                    anchors.leftMargin: 30
                    anchors.verticalCenter: parent.verticalCenter
                    width: 20
                    height: 20
                    source: "image://icons/arrow-right"
                    sourceSize: Qt.size(20, 20)
                    opacity: 0.7
                }

                FormatCombo {
                    id: formatControl
                    anchors.left: directionIcon.right
                    anchors.leftMargin: 38
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(226, parent.width * 0.18)
                    model: delegateRoot.targetOptions || []
                    leadingIcon: "image://icons/" + (
                        delegateRoot.mediaKind === "image"
                            ? "image"
                            : (delegateRoot.mediaKind === "audio" ? "music" : "film")
                    )
                    currentIndex: Math.max(0, (delegateRoot.targetOptions || []).indexOf(delegateRoot.targetFormat))
                    enabled: delegateRoot.jobStatus !== "running"
                    onActivated: jobController.setTargetFormat(delegateRoot.jobId, currentText)
                    Accessible.name: "Output format for " + delegateRoot.sourceName
                }

                Item {
                    id: statusArea
                    anchors.left: formatControl.right
                    anchors.leftMargin: 58
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    height: delegateRoot.jobStatus === "running" ? 66 : 56

                    Image {
                        id: statusIcon
                        anchors.left: parent.left
                        anchors.top: parent.top
                        width: 20
                        height: 20
                        source: delegateRoot.jobStatus === "succeeded"
                            ? "image://icons/check"
                            : (delegateRoot.jobStatus === "failed"
                                ? "image://icons/error"
                                : (delegateRoot.jobStatus === "queued" ? "image://icons/clock" : ""))
                        sourceSize: Qt.size(20, 20)
                        visible: delegateRoot.jobStatus === "succeeded"
                            || delegateRoot.jobStatus === "failed"
                            || delegateRoot.jobStatus === "queued"
                    }

                    Text {
                        id: statusTitleText
                        anchors.left: statusIcon.visible ? statusIcon.right : parent.left
                        anchors.leftMargin: statusIcon.visible ? 12 : 0
                        anchors.top: parent.top
                        text: delegateRoot.statusTitle
                            + (delegateRoot.jobStatus === "running" ? "  " + Math.round(delegateRoot.jobProgress * 100) + "%" : "")
                        color: delegateRoot.jobStatus === "failed" ? Theme.error : Theme.text
                        font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                        font.pixelSize: 15
                        font.weight: Font.Medium
                    }

                    Item {
                        id: linearProgress
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: statusTitleText.bottom
                        anchors.topMargin: 10
                        height: 4
                        visible: delegateRoot.jobStatus === "running"

                        Rectangle {
                            anchors.fill: parent
                            radius: 2
                            color: Theme.border
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: parent.width * Math.max(0, Math.min(1, delegateRoot.jobProgress))
                            radius: 2
                            color: Theme.accent

                            Behavior on width {
                                NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                            }
                        }
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        text: delegateRoot.statusSubtitle
                        color: delegateRoot.jobStatus === "failed" ? Theme.error : Theme.secondaryText
                        font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                    }

                    TapHandler {
                        enabled: delegateRoot.jobStatus === "succeeded"
                        onTapped: jobController.revealJob(delegateRoot.jobId)
                    }
                }
            }
        }
    }

    Item {
        id: emptyState
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !jobController.hasJobs

        Column {
            anchors.centerIn: parent
            spacing: 16

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 64
                height: 64
                source: "image://icons/file"
                sourceSize: Qt.size(64, 64)
                opacity: 0.52
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: jobController.probing ? "Reading files…" : window.tr("drop_anything")
                color: Theme.text
                font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: window.tr("drop_hint")
                color: Theme.secondaryText
                font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                font.pixelSize: 14
            }

            WButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: window.tr("choose_files")
                onClicked: fileDialog.open()
            }
        }
    }

    Rectangle {
        id: bottomBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 90
        color: Theme.windowDeep

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: Theme.divider
        }

        Button {
            id: destinationButton
            anchors.left: parent.left
            anchors.leftMargin: Theme.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            width: 188
            height: 48
            hoverEnabled: true
            onClicked: folderDialog.open()
            Accessible.name: jobController.destinationLabel

            contentItem: RowLayout {
                spacing: 12
                Image {
                    source: "image://icons/folder"
                    sourceSize: Qt.size(22, 22)
                    Layout.preferredWidth: 22
                    Layout.preferredHeight: 22
                    opacity: 0.85
                }
                Text {
                    text: jobController.destinationLabel === "Same Folder"
                        ? window.tr("same_folder")
                        : jobController.destinationLabel
                    color: Theme.secondaryText
                    font.family: Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Inter"
                    font.pixelSize: 15
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Image {
                    source: "image://icons/arrow-right"
                    sourceSize: Qt.size(12, 12)
                    Layout.preferredWidth: 12
                    Layout.preferredHeight: 12
                    rotation: 90
                    opacity: 0.6
                }
            }

            background: Rectangle {
                radius: Theme.radius
                color: destinationButton.hovered ? Theme.surfaceHover : Theme.transparent
            }
        }

        WButton {
            id: imageOptionsButton
            anchors.left: destinationButton.right
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            height: 42
            width: 132
            quiet: true
            text: window.tr("image_options")
            visible: jobController.hasImageJobs
            enabled: !jobController.busy
            onClicked: imageOptionsPopup.open()
            Accessible.name: text
        }

        WButton {
            id: aiToolsButton
            anchors.left: imageOptionsButton.visible ? imageOptionsButton.right : destinationButton.right
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            height: 42
            width: 104
            quiet: true
            text: window.tr("ai_tools")
            visible: jobController.hasImageJobs
            enabled: !jobController.busy
            onClicked: aiToolsPopup.open()
            Accessible.name: text
        }

        WButton {
            anchors.right: parent.right
            anchors.rightMargin: Theme.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            primary: true
            text: jobController.busy ? window.tr("cancel") : window.tr("convert_all")
            enabled: jobController.hasJobs && jobController.engineAvailable
            onClicked: {
                if (jobController.busy) {
                    jobController.cancelAll()
                    return
                }
                jobController.startAll()
            }
            Accessible.name: text
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: Theme.pageMargin
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            text: window.tr("engine_missing")
            color: Theme.error
            font.pixelSize: 11
            visible: !jobController.engineAvailable
        }
    }

    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list"]
        onDropped: function(drop) {
            if (drop.hasUrls) {
                jobController.addUrls(drop.urls)
                drop.acceptProposedAction()
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "#142B4A"
            opacity: parent.containsDrag ? 0.36 : 0
            border.width: parent.containsDrag ? 2 : 0
            border.color: Theme.accent
            visible: opacity > 0

            Behavior on opacity { NumberAnimation { duration: 120 } }
        }
    }
}
