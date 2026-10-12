import QtQuick
import "."

// Three soft elliptical glows on the base colour (top-left, top-right, bottom).
Canvas {
    id: canvas
    property bool dark: Theme.dark
    onDarkChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    function glow(ctx, cx, cy, rx, ry, color) {
        var c = Qt.color(color)
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(1, ry / rx)
        var gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, rx)
        gradient.addColorStop(0, Qt.rgba(c.r, c.g, c.b, c.a))
        gradient.addColorStop(0.35, Qt.rgba(c.r, c.g, c.b, c.a * 0.5))
        gradient.addColorStop(0.7, Qt.rgba(c.r, c.g, c.b, 0))
        ctx.fillStyle = gradient
        ctx.fillRect(-rx, -rx, rx * 2, rx * 2)
        ctx.restore()
    }

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = Theme.base
        ctx.fillRect(0, 0, width, height)
        glow(ctx, 0, 0, 700, 400, Theme.glow1)
        glow(ctx, width, height * 0.10, 600, 420, Theme.glow2)
        glow(ctx, width * 0.60, height * 1.20, 800, 500, Theme.glow3)
    }
}
