#!/usr/bin/env bash
# Build marsad_<version>_amd64.deb from the PyInstaller onedir output (dist/marsad/).
# Usage: bash packaging/linux/build_deb.sh <version>
set -euo pipefail
cd "$(dirname "$0")/../.."

VERSION="${1:-0.0.0}"
ARCH="amd64"
PKG="marsad"
ROOT="build/deb/${PKG}_${VERSION}_${ARCH}"

if [ ! -d dist/marsad ]; then
  echo "error: dist/marsad not found — run 'pyinstaller marsad.spec' first" >&2
  exit 1
fi

rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" \
         "$ROOT/opt/marsad" \
         "$ROOT/usr/bin" \
         "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/icons/hicolor/256x256/apps"

# app payload
cp -r dist/marsad/. "$ROOT/opt/marsad/"
chmod +x "$ROOT/opt/marsad/marsad"

# launcher symlink, desktop entry, icon
ln -sf /opt/marsad/marsad "$ROOT/usr/bin/marsad"
cp packaging/linux/marsad.desktop "$ROOT/usr/share/applications/marsad.desktop"
cp assets/marsad.png "$ROOT/usr/share/icons/hicolor/256x256/apps/marsad.png"

INSTALLED_KB=$(du -sk "$ROOT/opt" | cut -f1)

cat > "$ROOT/DEBIAN/control" <<EOF
Package: ${PKG}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: LTT PMO <pmo@example.com>
Installed-Size: ${INSTALLED_KB}
Depends: libc6, libglib2.0-0, libegl1, libgl1, libxkbcommon0, libfontconfig1, libdbus-1-3
Description: مرصد (marsad) — LTT 4G/5G project-management intelligence
 Arabic (RTL) desktop app that ingests field reports, runs them through a fleet
 of LLM agents, and produces an executive status brief plus PDF/Excel/HTML reports.
EOF

mkdir -p dist
OUT="dist/${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group --build "$ROOT" "$OUT"
echo "built: $OUT"
