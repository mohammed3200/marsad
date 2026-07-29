# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the marsad web API (Qt-free).

Builds a one-dir bundle at dist/marsad-api/:
    pyinstaller marsad_api.spec

Entry point is run_api.py, which starts the FastAPI app on 127.0.0.1.
"""
from PyInstaller.utils.hooks import collect_all, collect_submodules

ICON = "assets/marsad.ico"

datas = [
    ("settings.example.json", "."),
    ("sample_reports.json", "."),
    ("web/dist", "web/dist"),  # built web UI — run `cd web && npm run build` first
]
binaries = []
hiddenimports = []

# FastAPI/Starlette/Uvicorn and their lazy imports.
for pkg in ("fastapi", "starlette", "uvicorn"):
    hiddenimports += collect_submodules(pkg)

# Uvicorn loops/protocols/lifespan may be imported by name at runtime.
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "click",
    "logging.config",
    "h11",
]

# Core exporter dependencies (used by api/services.py -> core/exporters).
for pkg in ("reportlab", "openpyxl", "PyPDF2", "docx",
            "arabic_reshaper", "bidi"):
    hiddenimports += collect_submodules(pkg)

# python-docx pulls lxml.
_lx_datas, _lx_bins, _lx_hidden = collect_all("lxml")
datas += _lx_datas
binaries += _lx_bins
hiddenimports += _lx_hidden

a = Analysis(
    ["run_api.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PySide6", "PySide2", "PyQt6", "PyQt5", "shiboken6"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="marsad-api",
    icon=ICON,
    console=True,  # API server needs a console/log window
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="marsad-api", upx=False)
