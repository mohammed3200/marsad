"""Filesystem locations — source-run vs frozen (PyInstaller) app.

Two roots:
  BUNDLE_DIR — read-only bundled assets (qml/, assets/fonts/, seed configs).
               = sys._MEIPASS when frozen, else the repo root.
  DATA_DIR   — writable per-user state (settings.json, reports/, data/, logs/).
               = repo root when run from source; when frozen, a per-user dir
               (%APPDATA%/marsad, $XDG_DATA_HOME/marsad, or ~/.local/share/marsad).

An installed app cannot write next to its executable (Program Files, /opt), so
mutable state must live under DATA_DIR. Read-only defaults ship in BUNDLE_DIR and
are copied into DATA_DIR on first run via seed().
"""
import os
import sys
import shutil
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent


def _user_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "marsad"


if FROZEN:
    DATA_DIR = _user_data_dir()
else:
    DATA_DIR = Path(__file__).resolve().parent.parent

DATA_DIR.mkdir(parents=True, exist_ok=True)


def data_path(*parts) -> Path:
    """A writable path under DATA_DIR (parent dirs created)."""
    p = DATA_DIR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def bundle_path(*parts) -> Path:
    """A read-only path under BUNDLE_DIR (bundled asset / seed)."""
    return BUNDLE_DIR.joinpath(*parts)


def seed(*parts) -> Path:
    """Return the writable DATA_DIR copy of a bundled file, copying it on first run."""
    dst = data_path(*parts)
    if not dst.exists():
        src = bundle_path(*parts)
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return dst
