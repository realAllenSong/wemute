#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
APP_PATH="${1:-${PROJECT_DIR}/dist/Wemute.app}"
IDENTITY="${WEMUTE_SIGN_IDENTITY:-}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app bundle: $APP_PATH" >&2
  exit 1
fi
if [[ -z "$IDENTITY" ]]; then
  echo "Set WEMUTE_SIGN_IDENTITY to a Developer ID Application identity or SHA-1 hash." >&2
  exit 1
fi
if ! security find-identity -p codesigning -v | grep -Fq "$IDENTITY"; then
  echo "The requested signing identity is not available in this keychain: $IDENTITY" >&2
  exit 1
fi

# Sign every nested Mach-O item explicitly. Apple discourages using --deep to
# sign because it can miss nested code or apply the wrong options; verification
# still uses --deep after the inside-out signing pass.
while IFS= read -r -d '' item; do
  description="$(file -b "$item")"
  if [[ "$description" != *Mach-O* ]]; then
    continue
  fi
  options=(--force --timestamp --sign "$IDENTITY")
  if [[ "$description" == *executable* ]]; then
    options+=(--options runtime)
  fi
  codesign "${options[@]}" "$item"
done < <(find "$APP_PATH" -type f -print0)

# Seal framework bundles after their contained binaries, deepest paths first.
while IFS= read -r framework; do
  [[ -n "$framework" ]] || continue
  codesign --force --timestamp --sign "$IDENTITY" "$framework"
done < <(find "$APP_PATH" -type d -name '*.framework' -print | awk '{ print length, $0 }' | sort -rn | cut -d' ' -f2-)

codesign --force --timestamp --options runtime --sign "$IDENTITY" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
"$PROJECT_DIR/scripts/audit-macos-bundle.sh" "$APP_PATH" signed
echo "Developer ID signing complete: $APP_PATH"
