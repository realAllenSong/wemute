#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
SOURCE_ICON="${PROJECT_DIR}/src/wemute/assets/brand/wemute-app-icon-1024.png"
OUTPUT_ICON="${PROJECT_DIR}/build/Wemute.icns"

if [[ ! -f "$SOURCE_ICON" ]]; then
  echo "Missing source icon: $SOURCE_ICON" >&2
  exit 1
fi

if ! sips -g hasAlpha "$SOURCE_ICON" 2>/dev/null | rg -q 'hasAlpha: yes'; then
  echo "Source icon must contain transparency so macOS does not render a square canvas: $SOURCE_ICON" >&2
  exit 1
fi

ICON_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/wemute-icon.XXXXXX")"
trap 'rm -rf "$ICON_WORK_DIR"' EXIT
ICONSET_DIR="${ICON_WORK_DIR}/Wemute.iconset"
mkdir -p "$ICONSET_DIR" "${PROJECT_DIR}/build"

for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$SOURCE_ICON" --out "${ICONSET_DIR}/icon_${size}x${size}.png" >/dev/null
  retina_size=$((size * 2))
  sips -z "$retina_size" "$retina_size" "$SOURCE_ICON" --out "${ICONSET_DIR}/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT_ICON"
echo "Built $OUTPUT_ICON"
