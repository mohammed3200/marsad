"""Theme bridge — design tokens exposed to QML as the `Theme` context property.

Direction: "status brief on white paper". A light executive report for LTT's
4G/5G rollout — the calm of a printed briefing, not a SaaS dashboard. White
paper carries the surface; near-black ink carries the text; one deep telecom
teal-green accent appears sparingly (active tab, section tick). Colour is
rationed — status shows as a small dot or a single word, never a wall of tint.
Structure comes from hairline rules and generous space, not cards.

QML usage:  Theme.colors.ink,  Theme.fonts.body,  Theme.sp(4),  Theme.statusColor("جيد")
"""
from PySide6.QtCore import QObject, Property, Slot

_COLORS = {
    "bg":       "#FFFFFF",   # paper
    "panel":    "#FFFFFF",   # header / bars (separated by hairline, not fill)
    "fill":     "#F4F6F8",   # subtle section / zebra fill
    "card":     "#FFFFFF",
    "cardHi":   "#F7F9FA",
    "border":   "#E4E8EC",   # light hairline
    "borderHi": "#CFD6DD",   # stronger rule
    "ink":      "#141A22",   # primary text (~15:1 on white)
    "ink2":     "#5A6675",   # labels / secondary (~5.9:1)
    "ink3":     "#8A94A1",   # dim / caption (large / non-essential only)
    "accent":   "#0E6E60",   # deep telecom teal-green — used sparingly
    "accentHi": "#12897757",
    "accentLo": "#0B564B",
    "accentBg": "#E6F1EF",   # accent tint background
    # status — dark, print-safe; small dot / single word only
    "green":    "#1E7A52",   # good / safe / complete
    "amber":    "#946200",   # medium / warning (dark ochre; bright amber fails on white)
    "red":      "#B4232A",   # critical / danger / late
    "info":     "#1F5F8B",
    "white":    "#FFFFFF",
    # compat aliases (older QML references)
    "teal":     "#0E6E60",
    "tealHi":   "#0B564B",
    "tealLo":   "#0B564B",
    "violet":   "#5A6675",
}

_FONTS = {
    "display": "Noto Kufi Arabic",
    "body":    "Noto Sans Arabic",
    "mono":    "JetBrains Mono",
}

# fixed Arabic status literals -> semantic color key
_STATUS = {
    "جيد": "green", "متوسط": "amber", "حرج": "red",
    "تحذير": "amber",
    "آمن": "green", "خطر": "red",
    "عالية": "red", "متوسطة": "amber", "منخفضة": "green",
    "مكتمل": "green", "متأخر": "red", "في الموعد": "info",
}


class Theme(QObject):
    @Property("QVariantMap", constant=True)
    def colors(self):
        return _COLORS

    @Property("QVariantMap", constant=True)
    def fonts(self):
        return _FONTS

    @Slot(int, result=int)
    def sp(self, n):
        """spacing scale in px (4-based)"""
        return 4 * n

    @Slot(str, result=str)
    def statusColor(self, literal):
        return _COLORS.get(_STATUS.get(literal, ""), _COLORS["ink2"])
