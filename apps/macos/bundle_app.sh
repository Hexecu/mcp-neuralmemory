#!/usr/bin/env bash
# bundle_app.sh - Creates a proper .app bundle for NeuralMemoryAgent

set -euo pipefail

APP_NAME="NeuralMemoryAgent"
BUNDLE_ID="com.neuralcode.neuralmemoryagent"
BUILD_DIR=".build/debug"
APP_DIR="$APP_NAME.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

echo "🏗️ Building $APP_NAME..."
swift build

echo "📦 Creating app bundle..."

# Clean only the generated bundle in this directory.
if [[ "$APP_DIR" != "NeuralMemoryAgent.app" ]]; then
    echo "Refusing to replace an unexpected path: $APP_DIR" >&2
    exit 1
fi
rm -rf -- "$APP_DIR"
mkdir -p "$MACOS"
mkdir -p "$RESOURCES"

# Copy executable
cp "$BUILD_DIR/$APP_NAME" "$MACOS/"

# Copy icon if exists
if [ -d "NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset" ]; then
    # Create .icns from PNGs using iconutil
    ICONSET="$RESOURCES/AppIcon.iconset"
    mkdir -p "$ICONSET"
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_16.png "$ICONSET/icon_16x16.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_32.png "$ICONSET/icon_16x16@2x.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_32.png "$ICONSET/icon_32x32.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_64.png "$ICONSET/icon_32x32@2x.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_128.png "$ICONSET/icon_128x128.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_256.png "$ICONSET/icon_128x128@2x.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_256.png "$ICONSET/icon_256x256.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_512.png "$ICONSET/icon_256x256@2x.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_512.png "$ICONSET/icon_512x512.png" 2>/dev/null || true
    cp NeuralMemoryAgent/Assets.xcassets/AppIcon.appiconset/icon_1024.png "$ICONSET/icon_512x512@2x.png" 2>/dev/null || true

    iconutil -c icns "$ICONSET" -o "$RESOURCES/AppIcon.icns" 2>/dev/null || echo "⚠️ Could not create icns, using default icon"
    rm -rf "$ICONSET"
fi

# Create Info.plist
cat > "$CONTENTS/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.2.0</string>
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
    <string>When you enable activity capture, Neural Memory uses Accessibility access to record app and window context.</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>When you separately enable screenshots, Neural Memory uses Screen Recording to capture visual work context.</string>
</dict>
</plist>
EOF

# Create PkgInfo
echo -n "APPL????" > "$CONTENTS/PkgInfo"

echo "✅ App bundle created: $APP_DIR"
echo ""
echo "🚀 To run: open $APP_DIR"
echo "📂 To install: cp -r $APP_DIR /Applications/"
