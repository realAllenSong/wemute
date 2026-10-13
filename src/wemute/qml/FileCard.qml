import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

// A photo-like card, tilted by a deterministic angle so the stack feels
// physical. Hover straightens and lifts it and reveals ×.
Item {
    id: card
    required property string jobId
    required property string sourceName
    required property string thumbnailUrl
    required property string mediaKind
    required property string jobStatus
    required property real jobProgress
    required property bool rowSelected
    required property string errorText
    required property int cardIndex
    required property string durationLabel
    required property string sourceFormat
    required property string stage
    required property bool indeterminate
    required property real startedAt
    required property bool waiting
    property bool removable: true
    property bool showSelection: true

    signal selectRequested()
    signal quickLookRequested()
    signal removeRequested()

    readonly property var tilts: [-4, 2, -2, 3, -3, 1, -2, 4]
    readonly property bool lifted: hover.hovered
    readonly property bool isDone: jobStatus === "succeeded"
    readonly property bool isFailed: jobStatus === "failed"
    readonly property bool isRunning: jobStatus === "running"
    readonly property bool hasThumbnail: mediaKind !== "audio" && thumbnailUrl.length > 0
        && thumbnailUrl.indexOf("image://") !== 0
    readonly property bool isMedia: mediaKind === "image" || mediaKind === "video" || mediaKind === "audio"
    // Seconds since this file started, ticking while it runs.
    property real now: Date.now() / 1000
    readonly property int elapsed: isRunning && startedAt > 0 ? Math.max(0, Math.floor(now - startedAt)) : 0
    readonly property string elapsedLabel: {
        var minutes = Math.floor(elapsed / 60)
        var seconds = elapsed % 60
        if (i18n.language === "zh")
            return minutes > 0 ? minutes + " 分 " + seconds + " 秒" : seconds + " 秒"
        return minutes > 0 ? minutes + ":" + (seconds < 10 ? "0" : "") + seconds : seconds + "s"
    }
    readonly property string detailLine: {
        if (waiting)
            return stage
        if (!isRunning)
            return ""
        var parts = []
        if (stage.length > 0)
            parts.push(stage)
        if (indeterminate || !isMedia)
            parts.push(elapsedLabel)
        return parts.join(" · ")
    }

    Timer {
        interval: 1000
        repeat: true
        running: card.isRunning
        triggeredOnStart: true
        onTriggered: card.now = Date.now() / 1000
    }

    width: 118
    height: 148

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler {
        onTapped: card.selectRequested()
        onDoubleTapped: {
            card.selectRequested()
            card.quickLookRequested()
        }
    }

    ToolTip.visible: card.isFailed && hover.hovered && card.errorText.length > 0
    ToolTip.delay: 300
    ToolTip.text: card.errorText

    Item {
        id: body
        width: card.width
        height: card.height
        y: card.lifted ? -4 : 0
        rotation: card.lifted ? 0 : card.tilts[Math.max(0, card.cardIndex) % card.tilts.length]
        antialiasing: true
        Behavior on y { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        Behavior on rotation { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

        RectangularShadow {
            anchors.fill: face
            offset.y: card.lifted ? 16 : 10
            blur: card.lifted ? 30 : 24
            spread: -14
            radius: Theme.radiusCard
            color: Theme.cardShadow
            Behavior on offset.y { NumberAnimation { duration: 180 } }
        }

        Rectangle {
            id: face
            anchors.fill: parent
            radius: Theme.radiusCard
            color: Theme.card
            border.width: 1
            border.color: Theme.cardLine
            antialiasing: true
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -4
            radius: Theme.radiusCard + 4
            color: "transparent"
            border.width: 2
            border.color: Theme.cobaltText
            visible: card.rowSelected && card.showSelection
            antialiasing: true
        }

        Item {
            id: photo
            x: 6
            y: 6
            width: card.width - 12
            height: 104

            Rectangle {
                anchors.fill: parent
                radius: 15
                color: card.hasThumbnail ? Theme.photo : Theme.kindTint(card.mediaKind)
                antialiasing: true
            }

            // Cropped and rounded by the "thumbs" provider; no per-card effect.
            Image {
                id: thumb
                width: photo.width
                height: photo.height
                source: card.hasThumbnail ? "image://thumbs/15/" + encodeURIComponent(card.thumbnailUrl) : ""
                sourceSize: Qt.size(photo.width, photo.height)
                asynchronous: true
                antialiasing: true
            }

            Image {
                anchors.centerIn: parent
                visible: !card.hasThumbnail || thumb.status === Image.Error
                width: 34
                height: 34
                sourceSize: Qt.size(34, 34)
                source: visible
                    ? "image://icons/" + Theme.kindIcon(card.mediaKind)
                        + "/" + Theme.hex(Theme.kindColor(card.mediaKind)) + "/2"
                    : ""
            }

            // Source format for documents and other files: "DOCX", "PDF".
            Rectangle {
                visible: !card.isMedia && card.sourceFormat.length > 0
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 6
                width: formatText.implicitWidth + 12
                height: 18
                radius: 7
                color: Theme.kindColor(card.mediaKind)
                Text {
                    id: formatText
                    anchors.centerIn: parent
                    text: card.sourceFormat
                    color: Theme.dark ? "#10131C" : "#FFFFFF"
                    font.family: Theme.latinFont
                    font.pixelSize: 10
                    font.weight: Font.Bold
                }
            }

            // No measurable progress: a light sweep says it is still working.
            Item {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.bottomMargin: 5
                height: 3
                visible: card.isRunning && card.indeterminate
                clip: true
                Rectangle {
                    anchors.fill: parent
                    radius: 1.5
                    color: Theme.track
                }
                Rectangle {
                    id: sweep
                    width: parent.width * 0.4
                    height: parent.height
                    radius: 1.5
                    color: Theme.kindColor(card.mediaKind)
                    NumberAnimation on x {
                        running: card.isRunning && card.indeterminate
                        loops: Animation.Infinite
                        from: -sweep.width
                        to: sweep.parent.width
                        duration: 1300
                        easing.type: Easing.InOutQuad
                    }
                }
            }

            // Duration badge for video.
            Rectangle {
                visible: card.mediaKind === "video" && card.durationLabel.length > 0
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 6
                width: durationRow.implicitWidth + 12
                height: 18
                radius: 7
                color: Qt.rgba(15 / 255, 143 / 255, 126 / 255, 0.9)
                Row {
                    id: durationRow
                    anchors.centerIn: parent
                    spacing: 3
                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 8
                        height: 8
                        sourceSize: Qt.size(8, 8)
                        source: "image://icons/play/ffffff/1"
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: card.durationLabel
                        color: "#FFFFFF"
                        font.family: Theme.latinFont
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        font.features: { "tnum": 1 }
                    }
                }
            }

            // Status badge: check when done, red mark when failed, ring while converting.
            Rectangle {
                id: badge
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 6
                width: 22
                height: 22
                radius: 11
                color: card.isFailed ? Theme.error : Theme.cobalt
                visible: scale > 0.01
                scale: (card.isDone || card.isFailed) && !card.lifted ? 1 : 0
                Behavior on scale { NumberAnimation { duration: 260; easing.type: Easing.OutBack } }
                Image {
                    anchors.centerIn: parent
                    width: 12
                    height: 12
                    sourceSize: Qt.size(12, 12)
                    source: "image://icons/" + (card.isFailed ? "alert" : "check") + "/ffffff/3.5"
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 6
                width: 22
                height: 22
                radius: 11
                visible: card.isRunning
                color: Theme.dark ? Qt.rgba(13 / 255, 18 / 255, 32 / 255, 0.78) : Qt.rgba(1, 1, 1, 0.92)
                Canvas {
                    id: ring
                    anchors.fill: parent
                    anchors.margins: 3
                    property real value: card.indeterminate ? 0.28 : card.jobProgress
                    onValueChanged: requestPaint()
                    RotationAnimation on rotation {
                        running: card.isRunning && card.indeterminate
                        loops: Animation.Infinite
                        from: 0
                        to: 360
                        duration: 1100
                    }
                    rotation: 0
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        var r = width / 2 - 1.5
                        ctx.lineWidth = 2.5
                        ctx.lineCap = "round"
                        ctx.strokeStyle = Theme.track
                        ctx.beginPath()
                        ctx.arc(width / 2, height / 2, r, 0, Math.PI * 2)
                        ctx.stroke()
                        ctx.strokeStyle = Theme.cobaltText
                        ctx.beginPath()
                        ctx.arc(width / 2, height / 2, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0.06, value))
                        ctx.stroke()
                    }
                }
            }
        }

        Text {
            x: 10
            y: photo.y + photo.height + 6
            width: card.width - 20
            text: card.sourceName
            color: Theme.secondary
            font.family: Theme.fontFor(text)
            font.pixelSize: 11
            font.weight: Font.DemiBold
            elide: Text.ElideMiddle
        }

        // What the converter is doing right now: "正在启动文档引擎… · 12 秒".
        Text {
            x: 10
            y: photo.y + photo.height + 21
            width: card.width - 20
            visible: card.detailLine.length > 0
            text: card.detailLine
            color: Theme.muted
            font.family: Theme.fontFor(text)
            font.pixelSize: 10
            font.weight: Font.DemiBold
            font.features: { "tnum": 1 }
            elide: Text.ElideMiddle
        }

        // Remove, top-right on hover.
        Rectangle {
            id: removeButton
            anchors.right: face.right
            anchors.top: face.top
            anchors.rightMargin: -7
            anchors.topMargin: -7
            width: 24
            height: 24
            radius: 12
            color: removeHover.hovered ? Theme.error : (Theme.dark ? "#3A4360" : "#182033")
            border.width: 2
            border.color: Theme.card
            opacity: card.lifted && card.removable ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 120 } }
            Image {
                anchors.centerIn: parent
                width: 11
                height: 11
                sourceSize: Qt.size(11, 11)
                source: "image://icons/x/ffffff/3.5"
            }
            HoverHandler { id: removeHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: card.removeRequested() }
            Accessible.role: Accessible.Button
            Accessible.name: i18n.t("remove_card") + " " + card.sourceName
        }
    }
}
