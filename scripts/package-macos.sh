#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
APP_PATH="${PROJECT_DIR}/dist/Wemute.app"
LOCAL_ONLY=0
SKIP_BUILD=0

for argument in "$@"; do
  case "$argument" in
    --local) LOCAL_ONLY=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    *)
      echo "Usage: $0 [--local] [--skip-build]" >&2
      exit 2
      ;;
  esac
done

if [[ "$SKIP_BUILD" != "1" ]]; then
  "$PROJECT_DIR/scripts/build-macos.sh"
fi
"$PROJECT_DIR/scripts/audit-macos-bundle.sh" "$APP_PATH" local

VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP_PATH/Contents/Info.plist")"
RELEASE_DIR="${PROJECT_DIR}/dist/releases"
STAGE_DIR="${PROJECT_DIR}/build/dmg-stage"
mkdir -p "$RELEASE_DIR"

create_dmg() {
  local suffix="$1"
  local dmg_path="${RELEASE_DIR}/Wemute-${VERSION}-macos-arm64${suffix}.dmg"
  rm -rf "$STAGE_DIR"
  mkdir -p "$STAGE_DIR"
  ditto "$APP_PATH" "$STAGE_DIR/Wemute.app"
  ln -s /Applications "$STAGE_DIR/Applications"
  hdiutil create \
    -volname "Wemute ${VERSION}" \
    -srcfolder "$STAGE_DIR" \
    -format UDZO \
    -ov \
    "$dmg_path" >&2
  print -r -- "$dmg_path"
}

if [[ "$LOCAL_ONLY" == "1" ]]; then
  local_dmg="$(create_dmg '-local')"
  hdiutil verify "$local_dmg"
  shasum -a 256 "$local_dmg" > "${local_dmg}.sha256"
  echo "Created local test DMG: $local_dmg"
  exit 0
fi

if [[ -z "${WEMUTE_SIGN_IDENTITY:-}" ]]; then
  echo "Set WEMUTE_SIGN_IDENTITY before creating a public release." >&2
  exit 1
fi
if [[ -z "${WEMUTE_NOTARY_PROFILE:-}" ]]; then
  echo "Set WEMUTE_NOTARY_PROFILE to a notarytool Keychain profile." >&2
  exit 1
fi

"$PROJECT_DIR/scripts/sign-macos.sh" "$APP_PATH"

# First notarize and staple the app itself, then place that stapled app inside
# the final disk image. This keeps offline Gatekeeper verification reliable.
APP_ZIP="${RELEASE_DIR}/Wemute-${VERSION}-macos-arm64.zip"
ditto -c -k --keepParent "$APP_PATH" "$APP_ZIP"
xcrun notarytool submit "$APP_ZIP" --keychain-profile "$WEMUTE_NOTARY_PROFILE" --wait
xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"
"$PROJECT_DIR/scripts/audit-macos-bundle.sh" "$APP_PATH" notarized

DMG_PATH="$(create_dmg '')"
codesign --force --timestamp --sign "$WEMUTE_SIGN_IDENTITY" "$DMG_PATH"
xcrun notarytool submit "$DMG_PATH" --keychain-profile "$WEMUTE_NOTARY_PROFILE" --wait
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"
spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG_PATH"
hdiutil verify "$DMG_PATH"
shasum -a 256 "$APP_ZIP" "$DMG_PATH" > "${RELEASE_DIR}/Wemute-${VERSION}-macos-arm64.sha256"

echo "Created notarized release: $DMG_PATH"
