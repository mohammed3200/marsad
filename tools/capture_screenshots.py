#!/usr/bin/env python3
"""
Capture one PNG per tab of the marsad desktop app for the README gallery.

Requires an X display and:  pip install python-xlib   (Pillow is a project dep).
Run from the repo root:     python tools/capture_screenshots.py [out_dir]

It imports LTTApp directly (bypassing the first-run installer window), positions
the window on-screen, walks the notebook tab-by-tab, and grabs each tab straight
from the window's X drawable via Xlib (works without a compositor, unlike a
root-framebuffer grab). The dashboard tab is populated from reports/latest.json.
"""
import sys, os, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import tkinter as tk
from tkinter import ttk
from Xlib import X, display
from PIL import Image

import app as appmod  # importing runs the (no-op if installed) dependency check

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

# tab index -> output filename (order matches _build_ui)
NAMES = {
    0: "01-input.png", 1: "02-analysis.png", 2: "03-dashboard.png",
    3: "04-reports.png", 4: "05-settings.png", 5: "06-contacts.png",
}

_DISPLAY = display.Display()


def find_notebook(widget):
    if isinstance(widget, ttk.Notebook):
        return widget
    for child in widget.winfo_children():
        found = find_notebook(child)
        if found:
            return found
    return None


def settle(root, seconds=0.7):
    """Let Tk render, pumping the event loop (no mainloop)."""
    end = time.time() + seconds
    while time.time() < end:
        root.update_idletasks()
        root.update()
        time.sleep(0.02)


def grab_window(root, path, band=160):
    """Read the toplevel drawable in horizontal strips (a single GetImage of a
    large window can exceed the X max request length) and stitch them."""
    root.update_idletasks()
    xwin = _DISPLAY.create_resource_object("window", root.winfo_id())
    geo = xwin.get_geometry()
    w, h = geo.width, geo.height
    full = Image.new("RGB", (w, h))
    y = 0
    while y < h:
        bh = min(band, h - y)
        raw = xwin.get_image(0, y, w, bh, X.ZPixmap, 0xFFFFFFFF)
        strip = Image.frombytes("RGB", (w, bh), raw.data, "raw", "BGRX")
        full.paste(strip, (0, y))
        y += bh
    full.save(path)
    print(f"  saved {path.name}  ({w}x{h})")


def main():
    root = appmod.LTTApp()
    root.geometry("1320x820+40+30")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)
    settle(root, 1.3)  # first paint + fonts

    nb = find_notebook(root)
    if nb is None:
        print("ERROR: notebook not found", file=sys.stderr)
        root.destroy(); sys.exit(1)

    for i in range(len(nb.tabs())):
        nb.select(i)
        settle(root, 0.8)
        grab_window(root, OUT / NAMES.get(i, f"tab-{i}.png"))

    root.destroy()
    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()
