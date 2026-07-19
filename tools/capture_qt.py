#!/usr/bin/env python3
"""Screenshot harness — render each page of the QML app to PNG (offscreen).

Uses the real AppController (so the dashboard shows whatever is in
reports/latest.json). Run:  QT_QPA_PLATFORM=offscreen python tools/capture_qt.py [out_dir]
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import Qt, QUrl, QTimer, QEventLoop

from backend.theme import Theme
from backend.controller import AppController

PAGES = ["input", "analysis", "dashboard", "reports", "settings", "contacts"]


def load_fonts():
    for ttf in sorted((BASE / "assets" / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QGuiApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    load_fonts()

    theme, controller = Theme(), AppController()
    view = QQuickView()
    view.rootContext().setContextProperty("Theme", theme)
    view.rootContext().setContextProperty("app", controller)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(Qt.GlobalColor.white)
    view.resize(1280, 820)
    view.setSource(QUrl.fromLocalFile(str(BASE / "qml" / "Main.qml")))
    if view.status() == QQuickView.Status.Error:
        for e in view.errors():
            print("QML ERROR:", e.toString(), file=sys.stderr)
        return 1
    view.show()

    def settle(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    settle(600)
    controller.loadSamples()   # populate the Input list for the gallery
    settle(400)
    root = view.rootObject()
    for i, name in enumerate(PAGES):
        root.setProperty("currentIndex", i)
        settle(500)
        img = view.grabWindow()
        path = out_dir / f"{i}-{name}.png"
        img.save(str(path))
        print("saved", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
