#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
SPARKLE_VERSION="2.9.2"
SPARKLE_SHA256="1cb340cbbef04c6c0d162078610c25e2221031d794a3449d89f2f56f4df77c95"
SPARKLE_URL="https://github.com/sparkle-project/Sparkle/releases/download/${SPARKLE_VERSION}/Sparkle-${SPARKLE_VERSION}.tar.xz"
CACHE_DIR="${PROJECT_DIR}/build/vendor-cache"
ARCHIVE="${CACHE_DIR}/Sparkle-${SPARKLE_VERSION}.tar.xz"
RUNTIME_DIR="${PROJECT_DIR}/build/runtime/sparkle"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Sparkle is only bundled in the macOS application." >&2
  exit 1
fi
if [[ -d "${RUNTIME_DIR}/Sparkle.framework" \
  && -f "${RUNTIME_DIR}/LICENSE.txt" \
  && -f "${RUNTIME_DIR}/BUILD_INFO.txt" \
  && -x "${RUNTIME_DIR}/bin/generate_appcast" \
  && "${WEMUTE_REBUILD_SPARKLE:-0}" != "1" ]]; then
  echo "Using cached Sparkle runtime at $RUNTIME_DIR"
  exit 0
fi

mkdir -p "$CACHE_DIR" "${PROJECT_DIR}/build/runtime"
if [[ ! -f "$ARCHIVE" ]] || [[ "$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')" != "$SPARKLE_SHA256" ]]; then
  curl --fail --location --show-error "$SPARKLE_URL" --output "${ARCHIVE}.download"
  if [[ "$(shasum -a 256 "${ARCHIVE}.download" | awk '{print $1}')" != "$SPARKLE_SHA256" ]]; then
    rm -f "${ARCHIVE}.download"
    echo "Sparkle archive checksum did not match the pinned SHA-256." >&2
    exit 1
  fi
  mv "${ARCHIVE}.download" "$ARCHIVE"
fi

TEMP_BASE="${TMPDIR:-/tmp}"
TEMP_BASE="${TEMP_BASE%/}"
WORK_DIR="$(mktemp -d "${TEMP_BASE}/wemute-sparkle.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
tar -xf "$ARCHIVE" -C "$WORK_DIR" \
  ./Sparkle.framework \
  ./LICENSE \
  ./bin/generate_appcast \
  ./bin/generate_keys \
  ./bin/sign_update

NEW_RUNTIME="${WORK_DIR}/runtime"
mkdir -p "${NEW_RUNTIME}/bin"
ditto "${WORK_DIR}/Sparkle.framework" "${NEW_RUNTIME}/Sparkle.framework"
cp "${WORK_DIR}/LICENSE" "${NEW_RUNTIME}/LICENSE.txt"
cp "${WORK_DIR}/bin/generate_appcast" "${WORK_DIR}/bin/generate_keys" "${WORK_DIR}/bin/sign_update" "${NEW_RUNTIME}/bin/"
{
  echo "Sparkle ${SPARKLE_VERSION}"
  echo "Source: ${SPARKLE_URL}"
  echo "SHA-256: ${SPARKLE_SHA256}"
  echo "License: MIT"
} > "${NEW_RUNTIME}/BUILD_INFO.txt"

codesign --verify --deep --strict "${NEW_RUNTIME}/Sparkle.framework"
rm -rf "$RUNTIME_DIR"
mv "$NEW_RUNTIME" "$RUNTIME_DIR"
echo "Prepared Sparkle ${SPARKLE_VERSION} at $RUNTIME_DIR"
