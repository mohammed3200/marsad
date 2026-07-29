#!/usr/bin/env python3
"""Render Main.qml with the WhatsApp QR dialog forced open (fake matrix) —
verifies the QR grid delegate draws correctly, offscreen. One-shot harness."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import Qt, QUrl, QObject, Property, Signal

from backend.theme import Theme
from core.paths import BUNDLE_DIR

QML_DIR = BUNDLE_DIR / "qml"
FONT_DIR = BUNDLE_DIR / "assets" / "fonts"


class AppStub(QObject):
    notify = Signal(str)
    navRequested = Signal(int)

    def __init__(self, matrix):
        super().__init__()
        self._matrix = matrix

    @Property("QVariant", constant=True)
    def dashModel(self):
        return {}

    @Property(str, constant=True)
    def reportDate(self):
        return ""

    @Property(str, constant=True)
    def engineStatus(self):
        return "غير متصل"

    @Property(bool, constant=True)
    def engineOnline(self):
        return False

    @Property("QVariant", constant=True)
    def settings(self):
        return {"ai_backend": "ollama"}

    @Property(str, constant=True)
    def todayLabel(self):
        return "١٠ صفر ١٤٤٨ هـ · 2026-07-26"

    @Property(bool, constant=True)
    def waDialogOpen(self):
        return True

    @Property(bool, constant=True)
    def waLinked(self):
        return False

    @Property(str, constant=True)
    def waPhone(self):
        return ""

    @Property(bool, constant=True)
    def waStarting(self):
        return False

    @Property("QVariant", constant=True)
    def waQrMatrix(self):
        return self._matrix


def main():
    import qrcode
    q = qrcode.QRCode(border=0)
    q.add_data("MARSAD-GRID-RENDER-CHECK")
    q.make(fit=True)
    matrix = ["".join("1" if c else "0" for c in row) for row in q.get_matrix()]

    app = QGuiApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    for ttf in sorted(FONT_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))

    view = QQuickView()
    theme = Theme()              # keep refs alive — temporaries are GC'd and
    stub = AppStub(matrix)       # the context properties then read as null
    view.rootContext().setContextProperty("Theme", theme)
    view.rootContext().setContextProperty("app", stub)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(Qt.GlobalColor.white)
    view.resize(1280, 820)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if view.status() == QQuickView.Status.Error:
        for e in view.errors():
            print("QML ERROR:", e.toString(), file=sys.stderr)
        return 1
    view.show()
    app.processEvents()
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/wa_dialog_check.png"
    img = view.grabWindow()
    img.save(out)
    print("saved", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
