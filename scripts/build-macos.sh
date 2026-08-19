#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
cd "$PROJECT_DIR"

uv sync --dev
"$PROJECT_DIR/scripts/build-macos-icon.sh"
if [[ "${WEMUTE_SKIP_BUNDLED_FFMPEG:-0}" != "1" ]]; then
  "$PROJECT_DIR/scripts/build-ffmpeg-macos.sh"
fi
if [[ "${WEMUTE_SKIP_SPARKLE:-0}" != "1" ]]; then
  "$PROJECT_DIR/scripts/build-sparkle-macos.sh"
fi
APP_VERSION="$(uv run python -c 'from wemute import __version__; print(__version__)')"
APP_BUILD_NUMBER="${WEMUTE_BUILD_NUMBER:-$APP_VERSION}"
uv run pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name Wemute \
  --icon build/Wemute.icns \
  --osx-bundle-identifier com.wemute.app \
  --paths src \
  --additional-hooks-dir scripts/pyinstaller-hooks \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineQuick \
  --exclude-module PySide6.QtWebEngineWidgets \
  --add-data "src/wemute/qml:wemute/qml" \
  --add-data "src/wemute/assets:wemute/assets" \
  src/wemute/__main__.py

/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 14.0" dist/Wemute.app/Contents/Info.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 14.0" dist/Wemute.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :NSHighResolutionCapable bool true" dist/Wemute.app/Contents/Info.plist 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $APP_VERSION" dist/Wemute.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $APP_BUILD_NUMBER" dist/Wemute.app/Contents/Info.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $APP_BUILD_NUMBER" dist/Wemute.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string Wemute" dist/Wemute.app/Contents/Info.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName Wemute" dist/Wemute.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :LSApplicationCategoryType string public.app-category.utilities" dist/Wemute.app/Contents/Info.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :LSApplicationCategoryType public.app-category.utilities" dist/Wemute.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string 'Copyright © 2026 Wemute. All rights reserved.'" dist/Wemute.app/Contents/Info.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :NSHumanReadableCopyright 'Copyright © 2026 Wemute. All rights reserved.'" dist/Wemute.app/Contents/Info.plist

SPARKLE_PUBLIC_KEY="${WEMUTE_SPARKLE_PUBLIC_KEY:-}"
SPARKLE_FEED_URL="${WEMUTE_SPARKLE_FEED_URL:-https://github.com/realAllenSong/wemute/releases/latest/download/appcast.xml}"
if [[ -n "$SPARKLE_PUBLIC_KEY" ]]; then
  /usr/libexec/PlistBuddy -c "Add :SUPublicEDKey string $SPARKLE_PUBLIC_KEY" dist/Wemute.app/Contents/Info.plist
  /usr/libexec/PlistBuddy -c "Add :SUFeedURL string $SPARKLE_FEED_URL" dist/Wemute.app/Contents/Info.plist
  /usr/libexec/PlistBuddy -c "Add :SUAllowsAutomaticUpdates bool true" dist/Wemute.app/Contents/Info.plist
  /usr/libexec/PlistBuddy -c "Add :SUSendsSystemProfile bool false" dist/Wemute.app/Contents/Info.plist
fi

RUNTIME_DIR="$PROJECT_DIR/build/runtime/macos-arm64"
if [[ -d "$RUNTIME_DIR" ]]; then
  mkdir -p dist/Wemute.app/Contents/Resources/wemute/runtime
  ditto "$RUNTIME_DIR" dist/Wemute.app/Contents/Resources/wemute/runtime
fi
SPARKLE_RUNTIME="$PROJECT_DIR/build/runtime/sparkle"
if [[ -d "$SPARKLE_RUNTIME/Sparkle.framework" ]]; then
  ditto "$SPARKLE_RUNTIME/Sparkle.framework" dist/Wemute.app/Contents/Frameworks/Sparkle.framework
  mkdir -p dist/Wemute.app/Contents/Resources/wemute/sparkle
  cp "$SPARKLE_RUNTIME/LICENSE.txt" "$SPARKLE_RUNTIME/BUILD_INFO.txt" dist/Wemute.app/Contents/Resources/wemute/sparkle/
fi
codesign --force --deep --sign - dist/Wemute.app

echo "Built $PROJECT_DIR/dist/Wemute.app"
