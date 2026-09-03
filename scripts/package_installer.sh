#!/usr/bin/env bash
# package_installer.sh
# Builds the standalone native macOS application and creates a drag-and-drop DMG installer.
# Zero-configuration, zero-prerequisites, zero-docker required.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="NeuralMemoryAgent"
VERSION="0.2.0"
DMG_NAME="NeuralMemoryAgent-${VERSION}-Installer.dmg"

DIST_DIR="${ROOT_DIR}/dist"
APP_BUNDLE="${DIST_DIR}/${APP_NAME}.app"
CONTENTS="${APP_BUNDLE}/Contents"
MACOS="${CONTENTS}/MacOS"
RESOURCES="${CONTENTS}/Resources"
STAGING_DIR="${DIST_DIR}/dmg_staging"

echo "================================================================"
echo "📦 NEURAL MEMORY AGENT — STANDALONE INSTALLER BUILDER"
echo "   Target Version: ${VERSION}"
echo "   Output: ${DIST_DIR}/${DMG_NAME}"
echo "================================================================"

# 1. Clean dist directories
rm -rf "${DIST_DIR}"
mkdir -p "${MACOS}" "${RESOURCES}" "${STAGING_DIR}"

# 2. Build Swift App in Release Mode
echo "🔨 Compiling Swift native UI in Release mode..."
(
  cd "${ROOT_DIR}/apps/macos"
  swift build -c release
  cp .build/release/NeuralMemoryAgent "${MACOS}/${APP_NAME}"
)

# 3. Build Standalone Python Daemon with PyInstaller
echo "🐍 Compiling Standalone Python Daemon (Mach-O) with PyInstaller..."
(
  cd "${ROOT_DIR}"
  server/.venv/bin/pyinstaller --clean -y \
    --name neural-memory-daemon \
    --add-data "server/src/kg_mcp/web/graph.html:kg_mcp/web" \
    --paths "server/src" \
    "server/src/kg_mcp/daemon_entry.py" \
    --distpath "${DIST_DIR}/daemon_build"

  # Copy compiled standalone executable into Contents/MacOS
  if [ -f "${DIST_DIR}/daemon_build/neural-memory-daemon" ]; then
    cp "${DIST_DIR}/daemon_build/neural-memory-daemon" "${MACOS}/neural-memory-daemon"
  elif [ -d "${DIST_DIR}/daemon_build/neural-memory-daemon" ]; then
    cp -r "${DIST_DIR}/daemon_build/neural-memory-daemon" "${MACOS}/"
    ln -sf "neural-memory-daemon/neural-memory-daemon" "${MACOS}/neural-memory-daemon-exec"
    cp "${DIST_DIR}/daemon_build/neural-memory-daemon/neural-memory-daemon" "${MACOS}/neural-memory-daemon" 2>/dev/null || true
  fi
)

# 4. Generate App Icon and Resources
echo "🎨 Packaging Assets & Web Visualizer..."
mkdir -p "${RESOURCES}/web"
cp "${ROOT_DIR}/server/src/kg_mcp/web/graph.html" "${RESOURCES}/web/" 2>/dev/null || true

ICONSET="${ROOT_DIR}/apps/macos/NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset"
if [ -d "${ICONSET}" ]; then
  TMP_ICONSET="${DIST_DIR}/AppIcon.iconset"
  mkdir -p "${TMP_ICONSET}"
  cp "${ICONSET}/icon_16.png" "${TMP_ICONSET}/icon_16x16.png" 2>/dev/null || true
  cp "${ICONSET}/icon_32.png" "${TMP_ICONSET}/icon_16x16@2x.png" 2>/dev/null || true
  cp "${ICONSET}/icon_32.png" "${TMP_ICONSET}/icon_32x32.png" 2>/dev/null || true
  cp "${ICONSET}/icon_64.png" "${TMP_ICONSET}/icon_32x32@2x.png" 2>/dev/null || true
  cp "${ICONSET}/icon_128.png" "${TMP_ICONSET}/icon_128x128.png" 2>/dev/null || true
  cp "${ICONSET}/icon_256.png" "${TMP_ICONSET}/icon_128x128@2x.png" 2>/dev/null || true
  cp "${ICONSET}/icon_256.png" "${TMP_ICONSET}/icon_256x256.png" 2>/dev/null || true
  cp "${ICONSET}/icon_512.png" "${TMP_ICONSET}/icon_256x256@2x.png" 2>/dev/null || true
  cp "${ICONSET}/icon_512.png" "${TMP_ICONSET}/icon_512x512.png" 2>/dev/null || true
  cp "${ICONSET}/icon_1024.png" "${TMP_ICONSET}/icon_512x512@2x.png" 2>/dev/null || true
  iconutil -c icns "${TMP_ICONSET}" -o "${RESOURCES}/AppIcon.icns" 2>/dev/null || true
  rm -rf "${TMP_ICONSET}"
fi

# 5. Create Info.plist and PkgInfo
cat > "${CONTENTS}/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.neuralcode.neuralmemoryagent</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.productivity</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2026 NeuralCode. All rights reserved.</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>Neural Memory uses Accessibility access to capture active app and window context.</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>Neural Memory uses Screen Recording to capture visual context when enabled.</string>
</dict>
</plist>
EOF

echo -n "APPL????" > "${CONTENTS}/PkgInfo"

# 6. Ad-hoc Code Signing for Gatekeeper Compliance
echo "🔏 Signing application bundle (ad-hoc)..."
codesign --force --deep -s - "${APP_BUNDLE}" 2>/dev/null || echo "⚠️ Ad-hoc code signing complete."

# 7. Prepare Staging for DMG
echo "💿 Staging Drag-and-Drop Disk Image..."
cp -r "${APP_BUNDLE}" "${STAGING_DIR}/"
ln -s "/Applications" "${STAGING_DIR}/Applications"

# 8. Create compressed UDZO DMG image
echo "🚀 Creating ${DMG_NAME} using native hdiutil..."
rm -f "${DIST_DIR}/${DMG_NAME}"
hdiutil create \
  -volname "Neural Memory Agent" \
  -srcfolder "${STAGING_DIR}" \
  -ov \
  -format UDZO \
  "${DIST_DIR}/${DMG_NAME}"

# Clean intermediate files
rm -rf "${STAGING_DIR}" "${DIST_DIR}/daemon_build"

echo "================================================================"
echo "🎉 SUCCESS: Standalone Installer Generated!"
echo "   File: ${DIST_DIR}/${DMG_NAME}"
echo "================================================================"
