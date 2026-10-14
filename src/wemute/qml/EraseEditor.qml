import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window
import "."

// Paint over what should disappear. Strokes live in image pixels, so the mask
// is saved at the photo's full resolution whatever the zoom level.
Sheet {
    id: editor
    property string jobId: ""
    property url sourceUrl
    property bool applyGroup: false

    // On-screen brush diameter; strokes store it in image pixels.
    property real brush: 44
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    property bool spaceHeld: false
    readonly property bool comparing: compareButton.pressed
    property var strokes: []
    property var undoStack: []
    property var redoStack: []
    property int strokeCount: 0
    property int undoCount: 0
    property int redoCount: 0
    property bool drawing: false
    property string pendingMaskPath: ""

    readonly property int imageWidth: sourceImage.implicitWidth
    readonly property int imageHeight: sourceImage.implicitHeight
    readonly property bool ready: sourceImage.status === Image.Ready && imageWidth > 0
    readonly property real fitScale: ready
        ? Math.min((viewport.width - 48) / imageWidth, (viewport.height - 48) / imageHeight)
        : 1
    readonly property real viewScale: fitScale * zoom
    readonly property real maxZoom: Math.max(4, 4 / Math.max(0.01, fitScale))

    width: Math.min(1120, parent ? parent.width - 48 : 1120)
    height: Math.min(820, parent ? parent.height - 48 : 820)
    closePolicy: Popup.CloseOnEscape

    // Falls back to built-in strings for keys the catalogue does not have yet.
    function t(key, english, chinese) {
        var value = tr(key)
        return value !== key ? value : (i18n.language === "zh" ? chinese : english)
    }

    function openFor(id, url, group) {
        jobId = id
        applyGroup = group
        strokes = []
        undoStack = []
        redoStack = []
        syncCounts()
        zoom = 1
        panX = 0
        panY = 0
        brush = 44
        sourceUrl = url
        open()
        maskView.repaintAll()
    }

    onOpened: keyHandler.forceActiveFocus()
    onClosed: {
        spaceHeld = false
        drawing = false
    }

    function syncCounts() {
        strokeCount = strokes.length
        undoCount = undoStack.length
        redoCount = redoStack.length
    }

    // Image-space strokes; also used by tests and the visual QA harness.
    function beginStroke(x, y) {
        undoStack.push(strokes.slice())
        redoStack = []
        strokes.push({ "width": Math.max(1, brush / viewScale), "points": [{ "x": x, "y": y }] })
        drawing = true
        syncCounts()
        maskView.paintLatest()
    }
    function extendStroke(x, y) {
        if (!drawing || strokes.length === 0)
            return
        var points = strokes[strokes.length - 1].points
        var last = points[points.length - 1]
        // Skip sub-pixel moves (in screen space) to keep long strokes light.
        if (Math.abs(last.x - x) * viewScale < 1 && Math.abs(last.y - y) * viewScale < 1)
            return
        points.push({ "x": x, "y": y })
        maskView.paintLatest()
    }
    function endStroke() {
        drawing = false
    }
    function undo() {
        if (undoStack.length === 0)
            return
        redoStack.push(strokes)
        strokes = undoStack.pop()
        syncCounts()
        maskView.repaintAll()
    }
    function redo() {
        if (redoStack.length === 0)
            return
        undoStack.push(strokes)
        strokes = redoStack.pop()
        syncCounts()
        maskView.repaintAll()
    }
    function clearStrokes() {
        if (strokes.length === 0)
            return
        undoStack.push(strokes)
        redoStack = []
        strokes = []
        syncCounts()
        maskView.repaintAll()
    }

    function clampPan() {
        var spareX = Math.max(0, (imageWidth * viewScale - viewport.width) / 2 + 24)
        var spareY = Math.max(0, (imageHeight * viewScale - viewport.height) / 2 + 24)
        panX = Math.max(-spareX, Math.min(spareX, panX))
        panY = Math.max(-spareY, Math.min(spareY, panY))
    }
    function panBy(dx, dy) {
        panX += dx
        panY += dy
        clampPan()
    }
    // Zoom keeping the image point under (vx, vy) in place.
    function zoomTo(value, vx, vy) {
        var next = Math.max(1, Math.min(maxZoom, value))
        if (vx === undefined) {
            vx = viewport.width / 2
            vy = viewport.height / 2
        }
        var imageX = (vx - stage.x) / viewScale
        var imageY = (vy - stage.y) / viewScale
        var scale = fitScale * next
        zoom = next
        panX = vx - imageX * scale - (viewport.width - imageWidth * scale) / 2
        panY = vy - imageY * scale - (viewport.height - imageHeight * scale) / 2
        clampPan()
    }
    function fit() {
        zoom = 1
        panX = 0
        panY = 0
    }
    function toImage(vx, vy) {
        return Qt.point((vx - stage.x) / viewScale, (vy - stage.y) / viewScale)
    }

    function drawStroke(context, stroke, from) {
        var points = stroke.points
        context.lineWidth = stroke.width
        if (points.length === 1) {
            context.beginPath()
            context.arc(points[0].x, points[0].y, stroke.width / 2, 0, Math.PI * 2)
            context.fill()
            return
        }
        context.beginPath()
        var start = Math.max(0, from - 1)
        context.moveTo(points[start].x, points[start].y)
        for (var index = start + 1; index < points.length; index++)
            context.lineTo(points[index].x, points[index].y)
        context.stroke()
    }

    function applyMask() {
        var path = jobController.eraseMaskPath(jobId)
        if (path.length === 0)
            return
        pendingMaskPath = path
        exportCanvas.width = imageWidth / exportCanvas.ratio
        exportCanvas.height = imageHeight / exportCanvas.ratio
        exportCanvas.requestPaint()
    }

    Shortcut {
        enabled: editor.opened
        sequences: [StandardKey.Undo]
        onActivated: editor.undo()
    }
    Shortcut {
        enabled: editor.opened
        sequences: [StandardKey.Redo]
        onActivated: editor.redo()
    }
    Shortcut {
        enabled: editor.opened
        sequences: [StandardKey.ZoomIn, "Ctrl+="]
        onActivated: editor.zoomTo(editor.zoom * 1.25)
    }
    Shortcut {
        enabled: editor.opened
        sequences: [StandardKey.ZoomOut]
        onActivated: editor.zoomTo(editor.zoom / 1.25)
    }
    Shortcut {
        enabled: editor.opened
        sequence: "Ctrl+0"
        onActivated: editor.fit()
    }
    Shortcut {
        enabled: editor.opened
        sequence: "]"
        onActivated: editor.brush = Math.min(brushSlider.to, editor.brush + 6)
    }
    Shortcut {
        enabled: editor.opened
        sequence: "["
        onActivated: editor.brush = Math.max(brushSlider.from, editor.brush - 6)
    }
    Shortcut {
        enabled: editor.opened && editor.strokeCount > 0
        sequences: ["Return", "Enter"]
        onActivated: editor.applyMask()
    }

    contentItem: Item {
        id: keyHandler
        focus: true
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space) {
                if (!event.isAutoRepeat)
                    editor.spaceHeld = true
                event.accepted = true
            }
        }
        Keys.onReleased: function(event) {
            if (event.key === Qt.Key_Space && !event.isAutoRepeat) {
                editor.spaceHeld = false
                event.accepted = true
            }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ── header ──
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 18
                Layout.topMargin: 20
                Layout.bottomMargin: 14
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: editor.tr("erase_title")
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 22
                        font.weight: Font.ExtraBold
                    }
                    Text {
                        Layout.fillWidth: true
                        text: editor.tr("erase_hint")
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }
                WButton {
                    kind: "ghost"
                    iconName: "x"
                    implicitWidth: 34
                    onClicked: editor.close()
                    Accessible.name: editor.tr("cancel")
                }
            }

            // ── canvas ──
            Rectangle {
                id: viewportFrame
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                radius: 18
                color: Theme.dark ? "#0B0F1A" : "#E9EDF5"
                border.width: 1
                border.color: Theme.hairline

                Item {
                    id: viewport
                    anchors.fill: parent
                    anchors.margins: 1
                    clip: true

                    onWidthChanged: editor.clampPan()
                    onHeightChanged: editor.clampPan()

                    Item {
                        id: stage
                        width: editor.imageWidth
                        height: editor.imageHeight
                        transformOrigin: Item.TopLeft
                        scale: editor.viewScale
                        x: (viewport.width - width * scale) / 2 + editor.panX
                        y: (viewport.height - height * scale) / 2 + editor.panY
                        visible: editor.ready

                        RectangularShadow {
                            anchors.fill: parent
                            offset.y: 10 / Math.max(0.01, stage.scale)
                            blur: 30 / Math.max(0.01, stage.scale)
                            spread: -8 / Math.max(0.01, stage.scale)
                            color: Qt.rgba(0, 0, 0, Theme.dark ? 0.5 : 0.18)
                        }
                        Image {
                            id: sourceImage
                            anchors.fill: parent
                            source: editor.sourceUrl
                            autoTransform: true
                            asynchronous: true
                            cache: false
                            smooth: true
                            mipmap: true
                            fillMode: Image.Stretch
                            onStatusChanged: if (status === Image.Ready) maskView.repaintAll()
                        }

                        // Display copy of the mask, capped in size so live painting stays fast.
                        Canvas {
                            id: maskView
                            readonly property real factor: Math.min(1, 2560 / Math.max(1, Math.max(stage.width, stage.height)))
                            property bool fullRepaint: true
                            property int paintedStrokes: 0
                            property int paintedPoints: 0
                            width: Math.max(1, Math.round(stage.width * factor))
                            height: Math.max(1, Math.round(stage.height * factor))
                            transformOrigin: Item.TopLeft
                            scale: 1 / factor
                            renderTarget: Canvas.Image
                            renderStrategy: Canvas.Immediate
                            opacity: editor.comparing ? 0 : 0.58
                            Behavior on opacity { NumberAnimation { duration: 120 } }

                            function repaintAll() {
                                fullRepaint = true
                                requestPaint()
                            }
                            function paintLatest() {
                                requestPaint()
                            }
                            onWidthChanged: repaintAll()
                            onHeightChanged: repaintAll()

                            onPaint: {
                                var context = getContext("2d")
                                context.save()
                                context.scale(factor, factor)
                                context.strokeStyle = "#3D5CFF"
                                context.fillStyle = "#3D5CFF"
                                context.lineCap = "round"
                                context.lineJoin = "round"
                                var strokes = editor.strokes
                                if (fullRepaint) {
                                    context.clearRect(0, 0, stage.width, stage.height)
                                    for (var index = 0; index < strokes.length; index++)
                                        editor.drawStroke(context, strokes[index], 0)
                                    fullRepaint = false
                                } else {
                                    // Continue the last painted stroke, then any newer ones.
                                    for (var next = Math.max(0, paintedStrokes - 1); next < strokes.length; next++)
                                        editor.drawStroke(context, strokes[next], next === paintedStrokes - 1 ? paintedPoints : 0)
                                }
                                paintedStrokes = strokes.length
                                paintedPoints = strokes.length > 0 ? strokes[strokes.length - 1].points.length : 0
                                context.restore()
                            }
                        }
                    }

                    // Full-resolution mask, drawn once when applying.
                    Item {
                        width: 0
                        height: 0
                        clip: true
                        Canvas {
                            id: exportCanvas
                            // The backing image is width × the display's pixel ratio,
                            // so this makes the saved PNG exactly the photo's size.
                            readonly property real ratio: Math.max(1, Screen.devicePixelRatio)
                            width: 1
                            height: 1
                            renderTarget: Canvas.Image
                            renderStrategy: Canvas.Immediate
                            onPaint: {
                                if (editor.pendingMaskPath.length === 0)
                                    return
                                var context = getContext("2d")
                                context.save()
                                context.clearRect(0, 0, width, height)
                                context.scale(1 / ratio, 1 / ratio)
                                context.strokeStyle = "#FFFFFF"
                                context.fillStyle = "#FFFFFF"
                                context.lineCap = "round"
                                context.lineJoin = "round"
                                for (var index = 0; index < editor.strokes.length; index++)
                                    editor.drawStroke(context, editor.strokes[index], 0)
                                context.restore()
                            }
                            onPainted: {
                                var path = editor.pendingMaskPath
                                if (path.length === 0 || width <= 1)
                                    return
                                editor.pendingMaskPath = ""
                                var saved = save(path)
                                width = 1
                                height = 1
                                if (saved) {
                                    jobController.completeEraseMask(editor.jobId, path, editor.applyGroup)
                                    editor.close()
                                }
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: sourceImage.status === Image.Loading
                        text: editor.t("loading", "Loading photo…", "正在载入照片…")
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 14
                        font.weight: Font.Bold
                    }

                    MouseArea {
                        id: paintArea
                        anchors.fill: parent
                        enabled: editor.ready
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                        property bool panning: false
                        property point last
                        cursorShape: panning ? Qt.ClosedHandCursor
                            : (editor.spaceHeld ? Qt.OpenHandCursor : Qt.BlankCursor)

                        onPressed: function(mouse) {
                            keyHandler.forceActiveFocus()
                            if (editor.spaceHeld || mouse.button === Qt.MiddleButton) {
                                panning = true
                                last = Qt.point(mouse.x, mouse.y)
                                return
                            }
                            var point = editor.toImage(mouse.x, mouse.y)
                            editor.beginStroke(point.x, point.y)
                        }
                        onPositionChanged: function(mouse) {
                            if (panning) {
                                editor.panBy(mouse.x - last.x, mouse.y - last.y)
                                last = Qt.point(mouse.x, mouse.y)
                                return
                            }
                            if (pressed && editor.drawing) {
                                var point = editor.toImage(mouse.x, mouse.y)
                                editor.extendStroke(point.x, point.y)
                            }
                        }
                        onReleased: {
                            panning = false
                            editor.endStroke()
                        }
                        onCanceled: {
                            panning = false
                            editor.endStroke()
                        }
                        onWheel: function(wheel) {
                            var trackpad = wheel.pixelDelta.x !== 0 || wheel.pixelDelta.y !== 0
                            if (trackpad && !(wheel.modifiers & Qt.ControlModifier)) {
                                editor.panBy(wheel.pixelDelta.x, wheel.pixelDelta.y)
                            } else {
                                var delta = trackpad ? wheel.pixelDelta.y * 4 : wheel.angleDelta.y
                                editor.zoomTo(editor.zoom * Math.pow(1.0015, delta), wheel.x, wheel.y)
                            }
                            wheel.accepted = true
                        }
                    }

                    PinchHandler {
                        target: null
                        property real startZoom: 1
                        onActiveChanged: if (active) startZoom = editor.zoom
                        onActiveScaleChanged: editor.zoomTo(startZoom * activeScale, centroid.position.x, centroid.position.y)
                    }

                    // Live brush outline; also previews the size while the slider moves.
                    Item {
                        id: brushCursor
                        readonly property bool previewing: brushSlider.pressed || brushSlider.hovered
                        readonly property bool overCanvas: paintArea.containsMouse && !editor.spaceHeld && !paintArea.panning
                        visible: editor.ready && (overCanvas || previewing)
                        width: editor.brush
                        height: editor.brush
                        x: (overCanvas ? paintArea.mouseX : viewport.width / 2) - width / 2
                        y: (overCanvas ? paintArea.mouseY : viewport.height / 2) - height / 2

                        Rectangle {
                            anchors.fill: parent
                            radius: width / 2
                            color: brushCursor.previewing && !brushCursor.overCanvas ? Qt.rgba(61 / 255, 92 / 255, 1, 0.22) : "transparent"
                            border.width: 1.5
                            border.color: Qt.rgba(1, 1, 1, 0.95)
                        }
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: -1.5
                            radius: width / 2
                            color: "transparent"
                            border.width: 1
                            border.color: Qt.rgba(0, 0, 0, 0.45)
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 3
                            height: 3
                            radius: 1.5
                            color: Qt.rgba(1, 1, 1, 0.9)
                        }
                    }

                    // Zoom controls.
                    Rectangle {
                        id: zoomChip
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: 14
                        height: 36
                        width: zoomRow.implicitWidth + 8
                        radius: 12
                        color: Theme.dark ? Qt.rgba(31 / 255, 38 / 255, 57 / 255, 0.92) : Qt.rgba(1, 1, 1, 0.92)
                        border.width: 1
                        border.color: Theme.menuLine
                        visible: editor.ready

                        RectangularShadow {
                            anchors.fill: parent
                            z: -1
                            offset.y: 6
                            blur: 18
                            spread: -6
                            radius: parent.radius
                            color: Theme.menuShadow
                        }
                        Row {
                            id: zoomRow
                            anchors.centerIn: parent
                            spacing: 0
                            WButton {
                                kind: "ghost"
                                text: "−"
                                fontSize: 16
                                implicitWidth: 32
                                implicitHeight: 30
                                enabled: editor.zoom > 1.001
                                onClicked: editor.zoomTo(editor.zoom / 1.25)
                                Accessible.name: editor.t("zoom_out", "Zoom out", "缩小")
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 52
                                horizontalAlignment: Text.AlignHCenter
                                text: Math.round(editor.viewScale * 100) + "%"
                                color: Theme.ink
                                font.family: Theme.latinFont
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.features: { "tnum": 1 }
                            }
                            WButton {
                                kind: "ghost"
                                iconName: "plus"
                                iconSize: 13
                                implicitWidth: 32
                                implicitHeight: 30
                                enabled: editor.zoom < editor.maxZoom - 0.001
                                onClicked: editor.zoomTo(editor.zoom * 1.25)
                                Accessible.name: editor.t("zoom_in", "Zoom in", "放大")
                            }
                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 1
                                height: 18
                                color: Theme.hairline
                            }
                            WButton {
                                kind: "ghost"
                                text: editor.t("fit", "Fit", "适合")
                                implicitHeight: 30
                                enabled: editor.zoom > 1.001 || editor.panX !== 0 || editor.panY !== 0
                                onClicked: editor.fit()
                            }
                        }
                    }

                    // Shortcut hint.
                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottomMargin: 14
                        height: 30
                        width: hintText.implicitWidth + 28
                        radius: 15
                        color: Qt.rgba(12 / 255, 16 / 255, 28 / 255, 0.62)
                        visible: editor.ready
                        opacity: paintArea.pressed && !paintArea.panning ? 0 : 1
                        Behavior on opacity { NumberAnimation { duration: 160 } }
                        Text {
                            id: hintText
                            anchors.centerIn: parent
                            text: editor.comparing
                                ? editor.t("showing_original", "Showing the original", "正在显示原图")
                                : editor.t("erase_keys", "Space-drag to pan · ⌘+ / ⌘− to zoom · [ ] brush size",
                                           "按住空格拖动平移 · ⌘+ / ⌘− 缩放 · [ ] 调整笔刷")
                            color: "#FFFFFF"
                            font.family: Theme.font
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }

            // ── tools ──
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 20
                Layout.topMargin: 14
                Layout.bottomMargin: 18
                spacing: 8

                Text {
                    text: editor.tr("brush_size")
                    color: Theme.secondary
                    font.family: Theme.font
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }
                Item {
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.max(4, Math.min(26, editor.brush * 26 / brushSlider.to))
                        height: width
                        radius: width / 2
                        color: Theme.cobaltText
                        opacity: 0.85
                    }
                }
                Slider {
                    id: brushSlider
                    Layout.preferredWidth: 168
                    from: 6
                    to: 160
                    stepSize: 1
                    value: editor.brush
                    focusPolicy: Qt.NoFocus
                    hoverEnabled: true
                    onMoved: editor.brush = value
                    Accessible.name: editor.tr("brush_size")

                    background: Rectangle {
                        x: brushSlider.leftPadding
                        y: brushSlider.topPadding + brushSlider.availableHeight / 2 - height / 2
                        width: brushSlider.availableWidth
                        height: 6
                        radius: 3
                        color: Theme.track
                        Rectangle {
                            width: brushSlider.visualPosition * parent.width
                            height: parent.height
                            radius: 3
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: Theme.gradientTop }
                                GradientStop { position: 1; color: Theme.meterEnd }
                            }
                        }
                    }
                    handle: Item {
                        x: brushSlider.leftPadding + brushSlider.visualPosition * (brushSlider.availableWidth - width)
                        y: brushSlider.topPadding + brushSlider.availableHeight / 2 - height / 2
                        width: 20
                        height: 20
                        RectangularShadow {
                            anchors.fill: parent
                            offset.y: 2
                            blur: 8
                            radius: 10
                            color: Qt.rgba(30 / 255, 50 / 255, 110 / 255, 0.35)
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: 10
                            color: "#FFFFFF"
                            border.width: 1
                            border.color: Theme.secondaryLine
                            scale: brushSlider.pressed ? 1.1 : 1
                            Behavior on scale { NumberAnimation { duration: 110 } }
                        }
                    }
                }
                Text {
                    Layout.preferredWidth: 30
                    text: Math.round(editor.brush)
                    color: Theme.muted
                    font.family: Theme.latinFont
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    font.features: { "tnum": 1 }
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 20
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                    color: Theme.hairline
                }

                WButton {
                    kind: "ghost"
                    iconName: "retry"
                    text: editor.tr("undo")
                    enabled: editor.undoCount > 0
                    onClicked: editor.undo()
                }
                WButton {
                    kind: "ghost"
                    text: editor.t("redo", "Redo", "重做")
                    enabled: editor.redoCount > 0
                    onClicked: editor.redo()
                }
                WButton {
                    kind: "ghost"
                    iconName: "trash"
                    text: editor.tr("clear")
                    enabled: editor.strokeCount > 0
                    onClicked: editor.clearStrokes()
                }
                WButton {
                    id: compareButton
                    kind: "secondary"
                    text: editor.t("hold_compare", "Hold to compare", "按住对比")
                    enabled: editor.strokeCount > 0
                    Accessible.description: editor.t("hold_compare_hint", "Shows the original while held", "按住时显示原图")
                }

                Item { Layout.fillWidth: true }

                WButton {
                    kind: "ghost"
                    text: editor.tr("cancel")
                    implicitHeight: 38
                    onClicked: editor.close()
                }
                WButton {
                    kind: "primary"
                    implicitHeight: 38
                    text: editor.applyGroup ? editor.tr("apply_to_all") : editor.tr("apply")
                    enabled: editor.strokeCount > 0 && editor.ready && editor.pendingMaskPath.length === 0
                    onClicked: editor.applyMask()
                }
            }
        }
    }
}
