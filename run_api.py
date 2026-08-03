#!/usr/bin/env python3
"""Alternate entry point for the marsad web API.

Runs the FastAPI backend on 127.0.0.1 only. The same code is available as
``python -m api``; this script is provided for convenience and for PyInstaller.
"""
import os

import uvicorn

from api.app import app


def main():
    port = int(os.environ.get("MARSAD_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
