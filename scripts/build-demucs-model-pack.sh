#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
INPUT_DIR="${1:-}"
OUTPUT_PATH="${2:-$PROJECT_DIR/dist/model-packs/wemute-htdemucs-mlx-1.4.6.zip}"

if [[ -z "$INPUT_DIR" ]]; then
  echo "Usage: $0 <converted-model-directory> [output.zip]" >&2
  exit 2
fi

WEIGHTS="$INPUT_DIR/htdemucs.safetensors"
CONFIG="$INPUT_DIR/htdemucs_config.json"
if [[ ! -f "$WEIGHTS" || ! -f "$CONFIG" ]]; then
  echo "Expected htdemucs.safetensors and htdemucs_config.json in $INPUT_DIR" >&2
  exit 2
fi

EXPECTED_INNER=$(sed -n 's/.*"safetensors_sha256": "\([0-9a-f]*\)".*/\1/p' "$CONFIG")
ACTUAL_INNER=$(shasum -a 256 "$WEIGHTS" | awk '{print $1}')
if [[ ${#EXPECTED_INNER} -ne 64 || "$EXPECTED_INNER" != "$ACTUAL_INNER" ]]; then
  echo "The converted safetensors digest does not match its config." >&2
  exit 1
fi

STAGING=$(mktemp -d "${TMPDIR:-/tmp}/wemute-demucs-pack.XXXXXX")
trap 'rm -rf "$STAGING"' EXIT
mkdir -p "${OUTPUT_PATH:h}"
install -m 0644 "$WEIGHTS" "$STAGING/htdemucs.safetensors"
install -m 0644 "$CONFIG" "$STAGING/htdemucs_config.json"
install -m 0644 "$PROJECT_DIR/docs/model-packs/demucs-license.txt" "$STAGING/demucs-license.txt"
install -m 0644 "$PROJECT_DIR/docs/model-packs/htdemucs-notice.txt" "$STAGING/NOTICE.txt"

(
  cd "$STAGING"
  zip -X -9 -q "$OUTPUT_PATH" \
    htdemucs.safetensors htdemucs_config.json demucs-license.txt NOTICE.txt
)

echo "Built $OUTPUT_PATH"
wc -c < "$OUTPUT_PATH" | tr -d ' '
shasum -a 256 "$OUTPUT_PATH"
