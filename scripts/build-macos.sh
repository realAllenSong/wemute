#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
cd "$PROJECT_DIR"

uv sync --dev
uv run pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name Wemute \
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
codesign --force --deep --sign - dist/Wemute.app

echo "Built $PROJECT_DIR/dist/Wemute.app"
