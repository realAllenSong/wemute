import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// One file in a group card:  thumb · name   SOURCE ━━ target ▾   status   ×
// The seam between the source chip and the target is the signature element:
// it fills with cobalt as the file converts and stays lit once it is done.
Item {
    id: row
    required property string jobId
    required property string sourceName
    required property string metadata
    required property string thumbnailUrl
    required property string sourceFormat
    required property string targetFormat
    required property var targetOptions
    required property string mediaKind
    required property string jobStatus
    required property string statusTitle
    required property string resultSize
    required property string resultDelta
    required property string errorText
    required property real jobProgress
    required property bool rowSelected
    required property bool lastInGroup
    readonly property real progress: jobProgress

    signal selectRequested()
    signal openRequested()
    signal removeRequested()
    signal retryRequested()
    signal revealRequested()
    signal adjustRequested()
    signal menuRequested()
    signal targetChosen(string target)

    readonly property bool isRunning: jobStatus === "running"
    readonly property bool isDone: jobStatus === "succeeded"
    readonly property bool isFailed: jobStatus === "failed"
    readonly property bool active: hover.hovered || rowSelected

    function tr(key) {
        i18n.language
        return i18n.t(key)
    }

    implicitHeight: 70

    HoverHandler { id: hover }
    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: row.selectRequested()
        onDoubleTapped: row.openRequested()
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: row.menuRequested()
    }

    // Card body. Rows overlap by one pixel so neighbouring outlines merge.
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: -1
        color: row.rowSelected ? Theme.selected : (hover.hovered ? Theme.surfaceHover : Theme.surface)
        border.width: 1
        border.color: Theme.cardOutline
        bottomLeftRadius: row.lastInGroup ? Theme.radiusCard : 0
        bottomRightRadius: row.lastInGroup ? Theme.radiusCard : 0
    }

    // Selection marker on the leading edge.
    Rectangle {
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.verticalCenter: parent.verticalCenter
        width: 2
        height: 26
        radius: 1
        color: Theme.cobalt
        visible: row.rowSelected
    }

    Rectangle {
        id: thumb
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        width: 46
        height: 46
        radius: 9
        color: Theme.sunken

        Image {
            id: thumbImage
            anchors.fill: parent
            source: row.thumbnailUrl.indexOf("image://") === 0 ? "" : row.thumbnailUrl
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            sourceSize: Qt.size(120, 120)
            visible: false
        }
        // Clip the thumbnail to the tile's rounded corners.
        MultiEffect {
            anchors.fill: parent
            source: thumbImage
            visible: thumbImage.status === Image.Ready
            maskEnabled: true
            maskSource: thumbMask
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }
        Rectangle {
            id: thumbMask
            anchors.fill: parent
            radius: parent.radius
            visible: false
            layer.enabled: true
            layer.smooth: true
        }
        Image {
            anchors.centerIn: parent
            width: 18
            height: 18
            sourceSize: Qt.size(18, 18)
            visible: row.thumbnailUrl.indexOf("image://") === 0
            source: visible ? "image://icons/" + (row.mediaKind === "audio" ? "music" : (row.mediaKind === "video" ? "film" : "image"))
                + "/" + Theme.hex(Theme.mutedText) : ""
        }
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.width: 1
            border.color: Theme.hairline
        }
    }

    // ── right-hand cluster, laid out from the trailing edge ──────────────

    WButton {
        id: removeButton
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        width: 28
        height: 28
        kind: "ghost"
        iconName: "x"
        iconSize: 14
        opacity: row.active ? 1 : 0
        enabled: opacity > 0
        onClicked: row.removeRequested()
        Accessible.name: row.tr("remove") + " " + row.sourceName
        ToolTip.visible: hovered
        ToolTip.delay: 600
        ToolTip.text: row.tr("remove")
        Behavior on opacity { NumberAnimation { duration: 120 } }
    }

    Item {
        id: statusArea
        anchors.right: removeButton.left
        anchors.rightMargin: 8
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.max(128, Math.min(176, row.width * 0.17))

        Column {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            spacing: 4

            // Queued / cancelled: quiet text only.
            Text {
                visible: !row.isRunning && !row.isDone && !row.isFailed
                text: row.statusTitle
                color: Theme.mutedText
                font.family: Theme.uiFont
                font.pixelSize: 12
            }

            // Running: percentage in mono, the seam carries the bar.
            Row {
                visible: row.isRunning
                spacing: 6
                Text {
                    text: Math.round(row.progress * 100) + "%"
                    color: Theme.cobalt
                    font.family: Theme.monoFont
                    font.features: { "tnum": 1 }
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }
                Text {
                    anchors.baseline: parent.children[0].baseline
                    text: row.statusTitle
                    color: Theme.mutedText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                }
            }

            // Done: size and signed delta; click reveals in Finder.
            Row {
                visible: row.isDone
                spacing: 7
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 15
                    height: 15
                    sourceSize: Qt.size(15, 15)
                    source: row.isDone ? "image://icons/circle-check/" + Theme.hex(Theme.success) : ""
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: row.resultSize
                    color: doneLink.hovered ? Theme.cobalt : Theme.text
                    font.family: Theme.monoFont
                    font.features: { "tnum": 1 }
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    font.underline: doneLink.hovered
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: text.length > 0
                    text: row.resultDelta
                    color: row.resultDelta.indexOf("−") === 0 ? Theme.success : Theme.mutedText
                    font.family: Theme.monoFont
                    font.features: { "tnum": 1 }
                    font.pixelSize: 12
                }
            }

            // Failed: red label, the reason on hover, click to retry.
            Row {
                visible: row.isFailed
                spacing: 7
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 15
                    height: 15
                    sourceSize: Qt.size(15, 15)
                    source: row.isFailed ? "image://icons/circle-x/" + Theme.hex(Theme.error) : ""
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: row.statusTitle
                    color: Theme.error
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                    font.weight: Font.Medium
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "· " + row.tr("retry")
                    color: failLink.hovered ? Theme.text : Theme.mutedText
                    font.family: Theme.uiFont
                    font.pixelSize: 12
                    font.underline: failLink.hovered
                }
            }
        }

        HoverHandler {
            id: doneLink
            enabled: row.isDone
            cursorShape: Qt.PointingHandCursor
        }
        HoverHandler {
            id: failLink
            enabled: row.isFailed
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            enabled: row.isDone || row.isFailed
            onTapped: row.isDone ? row.revealRequested() : row.retryRequested()
        }
        ToolTip.visible: (failLink.hovered && row.errorText.length > 0) || (doneLink.hovered && row.isDone)
        ToolTip.delay: 350
        ToolTip.text: row.isFailed ? row.errorText : row.tr("reveal")
    }

    WButton {
        id: adjustButton
        anchors.right: statusArea.left
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        width: 30
        height: 30
        kind: "ghost"
        iconName: "settings"
        iconSize: 14
        visible: row.mediaKind === "image"
        opacity: row.active ? 1 : 0
        enabled: opacity > 0 && !row.isRunning
        onClicked: row.adjustRequested()
        Accessible.name: row.tr("adjust") + " " + row.sourceName
        ToolTip.visible: hovered
        ToolTip.delay: 500
        ToolTip.text: row.tr("adjust")
    }

    FormatCombo {
        id: targetCombo
        anchors.right: row.mediaKind === "image" ? adjustButton.left : statusArea.left
        anchors.rightMargin: row.mediaKind === "image" ? 4 : 44
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(132, Math.min(176, row.width * 0.17))
        height: 30
        model: row.targetOptions || []
        currentIndex: Math.max(0, (row.targetOptions || []).indexOf(row.targetFormat))
        emphasized: true
        enabled: !row.isRunning
        onActivated: row.targetChosen(currentText)
        Accessible.name: row.tr("save_to") + " " + row.sourceName
    }

    // The seam.
    Item {
        id: seam
        anchors.right: targetCombo.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        width: 34
        height: 8

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: 2
            radius: 1
            color: row.isFailed ? Theme.error : Theme.border
            opacity: row.isFailed ? 0.45 : 1
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            height: 2
            radius: 1
            width: parent.width * (row.isDone ? 1 : (row.isRunning ? Math.max(0.06, row.progress) : 0))
            color: Theme.cobalt
            Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        }
        // A small glowing head travels along the seam while converting.
        Rectangle {
            visible: row.isRunning
            anchors.verticalCenter: parent.verticalCenter
            x: parent.width * Math.max(0.06, row.progress) - width / 2
            width: 6
            height: 6
            radius: 3
            color: Theme.cobalt
            Rectangle {
                anchors.centerIn: parent
                width: 14
                height: 14
                radius: 7
                color: Theme.cobaltSoft
                SequentialAnimation on opacity {
                    running: row.isRunning
                    loops: Animation.Infinite
                    NumberAnimation { from: 1; to: 0.25; duration: 650; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 0.25; to: 1; duration: 650; easing.type: Easing.InOutSine }
                }
            }
            Behavior on x { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        }
    }

    Rectangle {
        id: sourceChip
        anchors.right: seam.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        width: sourceLabel.implicitWidth + 14
        height: 22
        radius: 6
        color: Theme.sunken

        Text {
            id: sourceLabel
            anchors.centerIn: parent
            text: row.sourceFormat
            color: Theme.secondaryText
            font.family: Theme.monoFont
            font.features: { "tnum": 1 }
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }

    Column {
        anchors.left: thumb.right
        anchors.leftMargin: 14
        anchors.right: sourceChip.left
        anchors.rightMargin: 18
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        Text {
            width: parent.width
            text: row.sourceName
            color: Theme.text
            font.family: Theme.uiFont
            font.pixelSize: 14
            font.weight: Font.Medium
            elide: Text.ElideMiddle
        }
        Text {
            width: parent.width
            text: row.metadata
            color: Theme.mutedText
            font.family: Theme.monoFont
            font.features: { "tnum": 1 }
            font.pixelSize: 11
            elide: Text.ElideRight
        }
    }
}
