import QtQuick

// Geometric marker drawn as a shape. The bundled fonts (Noto Kufi/Sans Arabic,
// JetBrains Mono) contain no symbol glyphs, so markers must never depend on
// system fallback fonts — draw them instead.
//
// Three construction rules keep the set reading as one family. The previous
// version broke all three, which is why the icons looked hand-made next to
// the type:
//
//  1. ONE OPTICAL BOX. Every shape is drawn inside the same inset of the item
//     (`m` below), so a bar chart and a chevron occupy the same visual square.
//     Before, most shapes used a 2px inset, `chevron` used ~3.5px, and `eye`
//     overshot the box by 1px — so they never sat on a common baseline.
//
//  2. ONE STROKE WEIGHT, SNAPPED TO THE PIXEL GRID. A 1px stroke centred on an
//     integer coordinate straddles two pixels and renders as two half-intensity
//     rows — grey mush instead of a line. Straight strokes are therefore placed
//     on half-pixels via `snap()`. Before, `lineWidth` was 1.6 on integer
//     coordinates, so every horizontal rule in the set was soft. Diagonals and
//     curves are left unsnapped: they are antialiased either way, and snapping
//     them only distorts the shape.
//
//  3. COMPARABLE INK. `grid` used to draw four 5px cells outlined at 1.6px —
//     roughly 64% coverage per cell, so it read as four blobs rather than a
//     grid, and shouted next to `bars` one row above it in the same sidebar.
//     Its cells are now sized so the two carry similar total ink.
//
// Judge changes here by rendering at the real size (15px in the sidebar) and
// magnifying the PNG with nearest-neighbour. At this scale a shape that reads
// fine in the source can be a smudge on screen, and vice versa.
Canvas {
    id: g
    property string shape: "square"   // bars|diamond|grid|square|dial|trigram|chevron|outline|eye|eyeoff
    property color  color: Theme.colors.ink3
    // Hairline, to match a design whose structure comes from hairline rules.
    property real   strokeWidth: 1
    width: 16; height: 16

    onColorChanged: requestPaint()
    onShapeChanged: requestPaint()
    onStrokeWidthChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = g.color
        ctx.fillStyle   = g.color
        ctx.lineWidth   = g.strokeWidth
        ctx.lineCap     = "butt"      // butt, not round: round adds half a
        ctx.lineJoin    = "miter"     // stroke of bloom at every rule's end

        var w = width, h = height
        // The shared optical box: an eighth of the item on each side, at least
        // 1px, so a 16px glyph draws in 12px and a 10px chevron in 8px.
        var m  = Math.max(1, Math.round(Math.min(w, h) * 0.125))
        // Odd stroke widths sit crisp on half-pixels, even ones on integers.
        var half = (Math.round(g.strokeWidth) % 2) ? 0.5 : 0
        function snap(v) { return Math.round(v) + half }

        var L = snap(m), R = snap(w - m)          // live box, snapped
        var T = snap(m), B = snap(h - m)
        var cx = snap(w / 2), cy = snap(h / 2)    // snapped centre, for strokes
        var mx = w / 2,       my = h / 2          // true centre, for curves

        function line(x1, y1, x2, y2) {
            ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
        }
        function strokeBox(x1, y1, x2, y2) {
            ctx.beginPath(); ctx.rect(x1, y1, x2 - x1, y2 - y1); ctx.stroke()
        }
        // Fills take integer edges — a filled rect on a half-pixel is exactly
        // the smear that snap() exists to avoid for strokes.
        function fillBox(x, y, bw, bh) {
            ctx.beginPath()
            ctx.rect(Math.round(x), Math.round(y), Math.round(bw), Math.round(bh))
            ctx.fill()
        }
        function dot(r) {
            ctx.beginPath(); ctx.arc(mx, my, r, 0, 2 * Math.PI); ctx.fill()
        }

        switch (g.shape) {
        case "bars":      // إدخال البيانات — three rules, evenly spaced
            for (var i = 0; i < 3; i++)
                line(L, snap(m + i * (h - 2 * m) / 2), R, snap(m + i * (h - 2 * m) / 2))
            break

        case "trigram":   // جهات الاتصال — bars, middle rule split
            line(L, T, R, T)
            line(L, cy, snap(w * 0.42), cy)
            line(snap(w * 0.58), cy, R, cy)
            line(L, B, R, B)
            break

        case "diamond":   // التحليل والوكلاء — diamond on the true centre
            ctx.beginPath()
            ctx.moveTo(mx, m); ctx.lineTo(w - m, my)
            ctx.lineTo(mx, h - m); ctx.lineTo(m, my)
            ctx.closePath(); ctx.stroke()
            dot(Math.max(1, (w - 2 * m) * 0.11))
            break

        case "grid": {    // لوحة التحكم — 2×2 cells at the corners of the box
            // Just under a third of the span. Filled blocks carry far more ink
            // per pixel than a 1px rule, so a full third out-weighed `bars`
            // directly above it in the sidebar; a quarter balanced but
            // collapsed to 3px cells that read as a colon rather than a grid.
            var span = w - 2 * m
            var cell = Math.max(2, Math.round(span * 0.32))
            fillBox(m,            m,            cell, cell)
            fillBox(w - m - cell, m,            cell, cell)
            fillBox(m,            h - m - cell, cell, cell)
            fillBox(w - m - cell, h - m - cell, cell, cell)
            break
        }

        case "square":    // التقارير — outlined sheet with a filled block
            strokeBox(L, T, R, B)
            var s = Math.max(2, Math.round((w - 2 * m) * 0.3))
            fillBox(mx - s / 2, my - s / 2, s, s)
            break

        case "dial":      // الإعدادات — ring with a spoke to 12 o'clock
            ctx.beginPath()
            ctx.arc(mx, my, (Math.min(w, h) - 2 * m) / 2, 0, 2 * Math.PI)
            ctx.stroke()
            line(cx, T, cx, snap(my - (Math.min(w, h) - 2 * m) * 0.18))
            break

        case "chevron":   // dropdown indicator — same box as everything else
            ctx.beginPath()
            ctx.moveTo(m, h * 0.38)
            ctx.lineTo(mx, h - m - (h * 0.38 - m))
            ctx.lineTo(w - m, h * 0.38)
            ctx.stroke()
            break

        case "outline":   // empty state — the bare box
            strokeBox(L, T, R, B)
            break

        case "eye":       // password visible — almond inside the box, no overshoot
        case "eyeoff":    // password hidden — the same, struck through
            ctx.beginPath()
            ctx.moveTo(m, my)
            ctx.quadraticCurveTo(mx, m, w - m, my)
            ctx.quadraticCurveTo(mx, h - m, m, my)
            ctx.stroke()
            dot(Math.max(1, (w - 2 * m) * 0.13))
            if (g.shape === "eyeoff")
                line(m, h - m, w - m, m)
            break
        }
    }
}
