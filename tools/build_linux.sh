#!/usr/bin/env bash
# Build a standalone Linux binary of marsad with pyside6-deploy (Nuitka).
# Requires: gcc, patchelf  (Debian/Ubuntu: sudo apt install patchelf)
# Output: dist/marsad
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v patchelf >/dev/null 2>&1; then
  echo "error: patchelf not found — install it (e.g. 'sudo apt install patchelf')" >&2
  exit 1
fi

python3 -m pip install --user --quiet nuitka
python3 -m PySide6.scripts.pyside_tool deploy -c pysidedeploy.spec --force || \
  pyside6-deploy -c pysidedeploy.spec --force

echo "built: dist/marsad"
