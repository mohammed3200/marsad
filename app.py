#!/usr/bin/env python3
"""
مرصد — marsad
LTT 4G/5G project-management intelligence, Arabic (RTL) desktop app.

Qt Quick / QML front-end (PySide6) over the UI-agnostic core (AI agents,
connectors, exporters, contacts). Run:  python app.py
"""
import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import Qt, QUrl

from backend.theme import Theme
from backend.controller import AppController
from core.paths import BUNDLE_DIR

QML_DIR  = BUNDLE_DIR / "qml"
FONT_DIR = BUNDLE_DIR / "assets" / "fonts"


def load_fonts():
    """Register bundled fonts so Arabic renders correctly without system fonts."""
    if not FONT_DIR.exists():
        return
    for ttf in sorted(FONT_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("مرصد")
    app.setOrganizationName("LTT")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    load_fonts()

    theme      = Theme()
    controller = AppController()

    view = QQuickView()
    view.setTitle("مرصد — منصّة ذكاء المشاريع")
    view.rootContext().setContextProperty("Theme", theme)
    view.rootContext().setContextProperty("app", controller)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(Qt.GlobalColor.white)
    view.resize(1280, 820)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))

    if view.status() == QQuickView.Status.Error:
        for e in view.errors():
            print("QML ERROR:", e.toString(), file=sys.stderr)
        return 1

    view.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
