#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
APP_PATH="${1:-${PROJECT_DIR}/dist/Wemute.app}"
MODE="${2:-local}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app bundle: $APP_PATH" >&2
  exit 1
fi

for required in \
  "$APP_PATH/Contents/MacOS/Wemute" \
  "$APP_PATH/Contents/Resources/wemute/runtime/bin/ffmpeg" \
  "$APP_PATH/Contents/Resources/wemute/runtime/bin/ffprobe" \
  "$APP_PATH/Contents/Resources/wemute/runtime/NOTICE.txt" \
  "$APP_PATH/Contents/Frameworks/Sparkle.framework" \
  "$APP_PATH/Contents/Resources/wemute/sparkle/LICENSE.txt" \
  "$APP_PATH/Contents/Resources/wemute/assets/THIRD_PARTY_NOTICES.txt"; do
  if [[ ! -e "$required" ]]; then
    echo "Release bundle is missing: $required" >&2
    exit 1
  fi
done

for forbidden in '*libx265*' '*pillow_heif*'; do
  if find "$APP_PATH" -iname "$forbidden" -print -quit | grep -q .; then
    echo "Release bundle contains forbidden component: $forbidden" >&2
    exit 1
  fi
done

dependency_report="$(
  while IFS= read -r -d '' item; do
    if file -b "$item" | grep -q 'Mach-O'; then
      otool -L "$item" 2>/dev/null || true
    fi
  done < <(find "$APP_PATH" -type f -print0)
)"
if print -r -- "$dependency_report" | grep -Eq '/opt/homebrew|/usr/local'; then
  echo "Release bundle still links to a package-manager path." >&2
  print -r -- "$dependency_report" | grep -E '/opt/homebrew|/usr/local' >&2
  exit 1
fi

ffmpeg="$APP_PATH/Contents/Resources/wemute/runtime/bin/ffmpeg"
if "$ffmpeg" -hide_banner -buildconf 2>&1 | grep -Eq -- '--enable-(gpl|nonfree)'; then
  echo "Bundled FFmpeg enables GPL or nonfree components." >&2
  exit 1
fi

codesign --verify --deep --strict "$APP_PATH"
"$APP_PATH/Contents/MacOS/Wemute" --audio-runtime-smoke-test

if [[ "$MODE" == "signed" || "$MODE" == "notarized" ]]; then
  if ! /usr/libexec/PlistBuddy -c 'Print :SUPublicEDKey' "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1; then
    echo "A public release must contain the Sparkle EdDSA public key." >&2
    exit 1
  fi
  signature="$(codesign --display --verbose=4 "$APP_PATH" 2>&1)"
  if ! print -r -- "$signature" | grep -q '^Authority=Developer ID Application:'; then
    echo "The app is not signed with a Developer ID Application identity." >&2
    exit 1
  fi
  if ! print -r -- "$signature" | grep -q '^Runtime Version='; then
    echo "The app does not have Hardened Runtime enabled." >&2
    exit 1
  fi
fi

if [[ "$MODE" == "notarized" ]]; then
  xcrun stapler validate "$APP_PATH"
  spctl --assess --type execute --verbose=2 "$APP_PATH"
fi

echo "Bundle audit passed ($MODE): $APP_PATH"
