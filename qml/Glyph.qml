import QtQuick

// Geometric marker drawn as a shape. The bundled fonts (Noto Kufi/Sans Arabic,
// JetBrains Mono) contain no symbol glyphs, so markers must never depend on
// system fallback fonts — draw them instead.
Canvas {
    id: g
    property string shape: "square"   // bars|diamond|grid|square|dial|trigram|chevron|outline
    property color  color: Theme.colors.ink3
    width: 16; height: 16

    onColorChanged: requestPaint()
    onShapeChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = g.color
        ctx.fillStyle   = g.color
        ctx.lineWidth   = 1.6
        ctx.lineCap     = "round"
        ctx.lineJoin    = "round"
        var w = width, h = height, m = 2
        function line(x1, y1, x2, y2) {
            ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
        }
        function box(x, y, bw, bh, fill) {
            ctx.beginPath(); ctx.rect(x, y, bw, bh); fill ? ctx.fill() : ctx.stroke()
        }
        switch (g.shape) {
        case "bars":      // إدخال البيانات — three horizontal rules
            line(m, h*0.25, w-m, h*0.25)
            line(m, h*0.50, w-m, h*0.50)
            line(m, h*0.75, w-m, h*0.75)
            break
        case "diamond":   // التحليل والوكلاء — diamond + centre dot
            ctx.beginPath()
            ctx.moveTo(w/2, m); ctx.lineTo(w-m, h/2)
            ctx.lineTo(w/2, h-m); ctx.lineTo(m, h/2)
            ctx.closePath(); ctx.stroke()
            box(w/2 - 1.5, h/2 - 1.5, 3, 3, true)
            break
        case "grid": {    // لوحة التحكم — 2×2 squares
            var s = (w - 3*m) / 2
            box(m,       m,       s, s, false)
            box(2*m + s, m,       s, s, false)
            box(m,       2*m + s, s, s, false)
            box(2*m + s, 2*m + s, s, s, false)
            break
        }
        case "square":    // التقارير — outer square, filled inner
            box(m, m, w - 2*m, h - 2*m, false)
            box(w*0.36, h*0.36, w*0.28, h*0.28, true)
            break
        case "dial":      // الإعدادات — ring + spoke
            ctx.beginPath()
            ctx.arc(w/2, h/2, (w - 2*m) / 2, 0, 2*Math.PI)
            ctx.stroke()
            line(w/2, h/2, w/2, m)
            break
        case "trigram":   // جهات الاتصال — bars, middle split
            line(m, h*0.25, w-m, h*0.25)
            line(m, h*0.50, w*0.40, h*0.50)
            line(w*0.60, h*0.50, w-m, h*0.50)
            line(m, h*0.75, w-m, h*0.75)
            break
        case "chevron":   // dropdown indicator
            ctx.beginPath()
            ctx.moveTo(w*0.22, h*0.34)
            ctx.lineTo(w*0.50, h*0.66)
            ctx.lineTo(w*0.78, h*0.34)
            ctx.stroke()
            break
        case "outline":   // empty state — hairline square
            box(m, m, w - 2*m, h - 2*m, false)
            break
        case "eye": {     // password visible — almond outline + pupil
            ctx.beginPath()
            ctx.moveTo(m, h/2)
            ctx.quadraticCurveTo(w/2, m - 1, w - m, h/2)
            ctx.quadraticCurveTo(w/2, h - m + 1, m, h/2)
            ctx.stroke()
            ctx.beginPath(); ctx.arc(w/2, h/2, 1.8, 0, 2*Math.PI); ctx.fill()
            break
        }
        case "eyeoff": {  // password hidden — eye + slash
            ctx.beginPath()
            ctx.moveTo(m, h/2)
            ctx.quadraticCurveTo(w/2, m - 1, w - m, h/2)
            ctx.quadraticCurveTo(w/2, h - m + 1, m, h/2)
            ctx.stroke()
            ctx.beginPath(); ctx.arc(w/2, h/2, 1.8, 0, 2*Math.PI); ctx.fill()
            line(w*0.22, h*0.80, w*0.78, h*0.20)
            break
        }
        }
    }
}
