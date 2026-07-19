# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for مرصد (marsad).

Bundles the QML tree, fonts, and seed configs; collects PySide6 (Qt plugins +
QtQuick.Controls.Basic QML) and the lazily-imported exporter deps.

Build onedir (for the NSIS installer + .deb):   pyinstaller marsad.spec
Build onefile portable exe:  MARSAD_ONEFILE=1 pyinstaller marsad.spec
"""
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

ONEFILE = bool(os.environ.get("MARSAD_ONEFILE"))
ICON = "assets/marsad.ico"

datas = [
    ("qml", "qml"),
    ("assets", "assets"),
    ("settings.example.json", "."),
    ("sample_reports.json", "."),
]
binaries = []
hiddenimports = []

for pkg in ("reportlab", "openpyxl", "PyPDF2"):
    hiddenimports += collect_submodules(pkg)

_ps_datas, _ps_bins, _ps_hidden = collect_all("PySide6")
datas += _ps_datas
binaries += _ps_bins
hiddenimports += _ps_hidden

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

# Trim the Qt bloat collect_all() pulls in — a QML app needs Core/Gui/Qml/Quick/
# QuickControls2/Network/Svg/OpenGL + platform+imageformat plugins, nothing else.
# Dropping these takes the bundle from ~880 MB to ~200 MB.
_EXCLUDE = (
    "Qt6WebEngine", "Qt6WebView", "QtWebEngine", "QtWebView", "webengine",
    "Qt6Quick3D", "QtQuick3D", "Qt63D", "Qt3D",
    "Qt6Charts", "QtCharts", "Qt6DataVisualization", "QtDataVisualization", "Qt6Graphs", "QtGraphs",
    "Qt6Multimedia", "QtMultimedia", "Qt6SpatialAudio", "QtSpatialAudio",
    "Qt6Pdf", "QtPdf", "Qt6VirtualKeyboard", "QtVirtualKeyboard",
    "Qt6Wayland", "QtWayland",
    "Qt6Sql", "sqldrivers", "Qt6Designer", "designer/libPySidePlugin", "Qt6Test",
    "Qt6Sensors", "QtSensors", "Qt6Bluetooth", "Qt6Nfc", "Qt6SerialPort", "Qt6SerialBus",
    "Qt6Positioning", "QtPositioning", "Qt6Location", "QtLocation",
    "Qt6TextToSpeech", "QtTextToSpeech", "Qt6RemoteObjects", "QtRemoteObjects",
    "Qt6Scxml", "QtScxml", "Qt6StateMachine", "Qt6WebSockets", "QtWebSockets",
    "Qt6WebChannel", "QtWebChannel", "Qt6ShaderTools", "Qt6Quick3DPhysics",
    "QtQuick/Scene2D", "QtQuick/Scene3D",
)

def _keep(dest):
    return not any(tok in dest for tok in _EXCLUDE)

a.binaries = [e for e in a.binaries if _keep(e[0])]
a.datas    = [e for e in a.datas if _keep(e[0])]

pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="marsad",
        console=False,
        icon=ICON,
        upx=False,
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="marsad",
        console=False,
        icon=ICON,
        upx=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="marsad", upx=False)
