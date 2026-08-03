"""Theme bridge — design tokens exposed to QML as the `Theme` context property.

Direction: "status brief on white paper". A light executive report for LTT's
4G/5G rollout — the calm of a printed briefing, not a SaaS dashboard. White
paper carries the surface; near-black ink carries the text; one deep telecom
teal-green accent appears sparingly (active tab, section tick). Colour is
rationed — status shows as a small dot or a single word, never a wall of tint.
Structure comes from hairline rules and generous space, not cards.

QML usage:  Theme.colors.ink,  Theme.fonts.body,  Theme.fs.body,  Theme.statusColor("جيد")
"""
from PySide6.QtCore import QObject, Property, Slot

_COLORS = {
    "bg":       "#FFFFFF",   # paper
    "panel":    "#FFFFFF",   # header / bars (separated by hairline, not fill)
    "fill":     "#F4F6F8",   # subtle section / zebra fill
    "cardHi":   "#F7F9FA",
    "border":   "#E4E8EC",   # light hairline
    "borderHi": "#CFD6DD",   # stronger rule
    "ink":      "#141A22",   # primary text (~15:1 on white)
    "ink2":     "#5A6675",   # labels / secondary (~5.9:1)
    "ink3":     "#8A94A1",   # dim / caption (large / non-essential only)
    "accent":   "#0E6E60",   # deep telecom teal-green — used sparingly
    "accentLo": "#0B564B",
    "accentBg": "#E6F1EF",   # accent tint background
    "accentSoft": "#EEF6F4", # softer accent wash — nav pill / quiet panels
    # status — dark, print-safe; small dot / single word only
    "green":    "#1E7A52",   # good / safe / complete
    "amber":    "#946200",   # medium / warning (dark ochre; bright amber fails on white)
    "red":      "#B4232A",   # critical / danger / late
    "redHi":    "#912018",   # darker red — danger hover
    "info":     "#1F5F8B",
    # compat aliases (older QML references)
    "teal":     "#0E6E60",
    "tealHi":   "#0B564B",
}

_FONTS = {
    "display": "Noto Kufi Arabic",
    "body":    "Noto Sans Arabic",
    "mono":    "JetBrains Mono",
}

# Arabic-forward type scale (px). Kufi carries display; Sans carries reading.
_FS = {
    "hero":    34,   # page/brand hero
    "display": 26,   # page titles
    "title":   20,   # sub-headings
    "section": 17,   # section labels
    "body":    14,   # reading
    "small":   13,   # dense labels
    "caption": 11,   # captions / meta
}


class Theme(QObject):
    @Property("QVariantMap", constant=True)
    def colors(self):
        return _COLORS

    @Property("QVariantMap", constant=True)
    def fonts(self):
        return _FONTS

    @Property("QVariantMap", constant=True)
    def fs(self):
        return _FS

    @Slot(str, result=str)
    def statusColor(self, literal):
        from core.status import tier
        return {"good": _COLORS["green"], "warn": _COLORS["amber"],
                "bad": _COLORS["red"], "neutral": _COLORS["ink2"]}[tier(literal)]
