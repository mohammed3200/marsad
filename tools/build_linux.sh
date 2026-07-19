#!/usr/bin/env bash
# Build the Linux binary (PyInstaller onedir) and a .deb package.
# Requires: pip deps + pyinstaller, dpkg-deb.
# Output: dist/marsad/  and  dist/marsad_<version>_amd64.deb
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-1.0.0}"

python3 -m pip install --user --quiet pyinstaller
pyinstaller --noconfirm marsad.spec
bash packaging/linux/build_deb.sh "$VERSION"

echo "done: dist/marsad/  +  dist/marsad_${VERSION}_amd64.deb"
