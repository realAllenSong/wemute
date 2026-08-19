#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
FFMPEG_VERSION="8.1.2"
FFMPEG_SHA256="464beb5e7bf0c311e68b45ae2f04e9cc2af88851abb4082231742a74d97b524c"
FFMPEG_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz"
RUNTIME_DIR="${PROJECT_DIR}/build/runtime/macos-arm64"
CACHE_DIR="${PROJECT_DIR}/build/vendor-cache"
ARCHIVE="${CACHE_DIR}/ffmpeg-${FFMPEG_VERSION}.tar.xz"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This runtime builder currently targets macOS arm64." >&2
  exit 1
fi

if [[ -x "${RUNTIME_DIR}/bin/ffmpeg" && -x "${RUNTIME_DIR}/bin/ffprobe" && "${WEMUTE_REBUILD_FFMPEG:-0}" != "1" ]]; then
  echo "Using cached FFmpeg runtime at $RUNTIME_DIR"
  exit 0
fi

for formula in lame opus libvpx pkgconf; do
  if ! brew --prefix "$formula" >/dev/null 2>&1; then
    echo "Missing Homebrew build dependency: $formula" >&2
    echo "Install it with: brew install lame opus libvpx pkgconf" >&2
    exit 1
  fi
done

mkdir -p "$CACHE_DIR" "${PROJECT_DIR}/build/runtime"
if [[ ! -f "$ARCHIVE" ]] || [[ "$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')" != "$FFMPEG_SHA256" ]]; then
  curl --fail --location --show-error "$FFMPEG_URL" --output "${ARCHIVE}.download"
  if [[ "$(shasum -a 256 "${ARCHIVE}.download" | awk '{print $1}')" != "$FFMPEG_SHA256" ]]; then
    rm -f "${ARCHIVE}.download"
    echo "FFmpeg source checksum did not match the pinned SHA-256." >&2
    exit 1
  fi
  mv "${ARCHIVE}.download" "$ARCHIVE"
fi

TEMP_BASE="${TMPDIR:-/tmp}"
TEMP_BASE="${TEMP_BASE%/}"
WORK_DIR="$(mktemp -d "${TEMP_BASE}/wemute-ffmpeg.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
SOURCE_DIR="${WORK_DIR}/ffmpeg-${FFMPEG_VERSION}"
STAGE_DIR="${WORK_DIR}/stage"
tar -xf "$ARCHIVE" -C "$WORK_DIR"

PKG_CONFIG_DIR="${WORK_DIR}/pkgconfig"
mkdir -p "$PKG_CONFIG_DIR"
{
  echo "prefix=$(brew --prefix lame)"
  echo 'exec_prefix=${prefix}'
  echo 'libdir=${exec_prefix}/lib'
  echo 'includedir=${prefix}/include'
  echo
  echo 'Name: lame'
  echo 'Description: LAME MP3 encoder'
  echo 'Version: 3.100'
  echo 'Libs: -L${libdir} -lmp3lame'
  echo 'Cflags: -I${includedir}'
} > "${PKG_CONFIG_DIR}/lame.pc"
export PKG_CONFIG_PATH="${PKG_CONFIG_DIR}:$(brew --prefix opus)/lib/pkgconfig:$(brew --prefix libvpx)/lib/pkgconfig"
CONFIGURE_FLAGS=(
  "--prefix=${STAGE_DIR}"
  "--arch=arm64"
  "--target-os=darwin"
  "--cc=clang"
  "--extra-cflags=-I$(brew --prefix lame)/include -I$(brew --prefix opus)/include -I$(brew --prefix libvpx)/include"
  "--extra-ldflags=-L$(brew --prefix lame)/lib -L$(brew --prefix opus)/lib -L$(brew --prefix libvpx)/lib"
  "--disable-debug"
  "--disable-doc"
  "--disable-ffplay"
  "--disable-devices"
  "--disable-avfoundation"
  "--disable-sdl2"
  "--disable-xlib"
  "--disable-libxcb"
  "--disable-libxcb-shm"
  "--disable-libxcb-shape"
  "--disable-libxcb-xfixes"
  "--disable-static"
  "--enable-shared"
  "--disable-gpl"
  "--disable-nonfree"
  "--enable-audiotoolbox"
  "--enable-videotoolbox"
  "--enable-libmp3lame"
  "--enable-libopus"
  "--enable-libvpx"
  "--enable-neon"
)

cd "$SOURCE_DIR"
if ! ./configure "${CONFIGURE_FLAGS[@]}"; then
  tail -n 120 ffbuild/config.log >&2
  exit 1
fi
make -j "$(sysctl -n hw.logicalcpu)"
make install

NEW_RUNTIME="${WORK_DIR}/runtime"
mkdir -p "${NEW_RUNTIME}/bin" "${NEW_RUNTIME}/lib" "${NEW_RUNTIME}/licenses"
cp "${STAGE_DIR}/bin/ffmpeg" "${STAGE_DIR}/bin/ffprobe" "${NEW_RUNTIME}/bin/"
for library in "${STAGE_DIR}/lib/"*.dylib; do
  library_name="$(basename "$library")"
  # Keep only the ABI name linked by the executables (for example
  # libavcodec.62.dylib). Copying the generic and fully versioned aliases as
  # separate files nearly triples the runtime without adding compatibility.
  if [[ "$library_name" =~ '^lib[^.]+\.[0-9]+\.dylib$' ]]; then
    cp -L "$library" "${NEW_RUNTIME}/lib/${library_name}"
  fi
done

copy_formula_library() {
  local formula="$1"
  local pattern="$2"
  local source
  source="$(find -L "$(brew --prefix "$formula")/lib" -maxdepth 1 -type f -name "$pattern" | head -n 1)"
  if [[ -z "$source" ]]; then
    echo "Could not locate runtime library for $formula ($pattern)." >&2
    exit 1
  fi
  cp "$source" "${NEW_RUNTIME}/lib/$(basename "$source")"
}

copy_formula_library lame 'libmp3lame.*.dylib'
copy_formula_library opus 'libopus.*.dylib'
copy_formula_library libvpx 'libvpx.*.dylib'

rewrite_dependencies() {
  local target="$1"
  local dependency
  local dependency_name
  while IFS= read -r dependency; do
    dependency_name="$(basename "$dependency")"
    if [[ -f "${NEW_RUNTIME}/lib/${dependency_name}" ]]; then
      install_name_tool -change "$dependency" "@rpath/${dependency_name}" "$target"
    fi
  done < <(otool -L "$target" | tail -n +2 | awk '{print $1}')
}

for library in "${NEW_RUNTIME}/lib/"*.dylib; do
  install_name_tool -id "@rpath/$(basename "$library")" "$library"
  rewrite_dependencies "$library"
done
for executable in "${NEW_RUNTIME}/bin/ffmpeg" "${NEW_RUNTIME}/bin/ffprobe"; do
  rewrite_dependencies "$executable"
  install_name_tool -add_rpath '@executable_path/../lib' "$executable"
done

cp COPYING.LGPLv2.1 "${NEW_RUNTIME}/licenses/FFmpeg-LGPL-2.1.txt"
cp "$(brew --prefix lame)/COPYING" "${NEW_RUNTIME}/licenses/LAME-LGPL.txt"
cp "$(brew --prefix opus)/COPYING" "${NEW_RUNTIME}/licenses/Opus-BSD.txt"
cp "$(brew --prefix libvpx)/LICENSE" "${NEW_RUNTIME}/licenses/libvpx-BSD.txt"
cp "${PROJECT_DIR}/docs/ffmpeg-runtime-notice.txt" "${NEW_RUNTIME}/NOTICE.txt"
{
  echo "FFmpeg ${FFMPEG_VERSION}"
  echo "Source: ${FFMPEG_URL}"
  echo "SHA-256: ${FFMPEG_SHA256}"
  echo "Configure flags: ${CONFIGURE_FLAGS[*]}"
  echo "LAME: $(brew list --versions lame)"
  echo "Opus: $(brew list --versions opus)"
  echo "libvpx: $(brew list --versions libvpx)"
  echo "Built on: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${NEW_RUNTIME}/BUILD_INFO.txt"

for item in "${NEW_RUNTIME}/lib/"*.dylib "${NEW_RUNTIME}/bin/ffmpeg" "${NEW_RUNTIME}/bin/ffprobe"; do
  codesign --force --sign - "$item" >/dev/null
done

if "${NEW_RUNTIME}/bin/ffmpeg" -hide_banner -buildconf 2>&1 | grep -Eq -- '--enable-(gpl|nonfree)'; then
  echo "Refusing a GPL or nonfree FFmpeg runtime." >&2
  exit 1
fi
if find "$NEW_RUNTIME" -type f -print0 | xargs -0 otool -L 2>/dev/null | grep -Eq '/opt/homebrew|/usr/local'; then
  echo "The FFmpeg runtime still references a package-manager path." >&2
  exit 1
fi

rm -rf "$RUNTIME_DIR"
mv "$NEW_RUNTIME" "$RUNTIME_DIR"
"${RUNTIME_DIR}/bin/ffmpeg" -hide_banner -version | head -n 1
echo "Built LGPL-compatible runtime at $RUNTIME_DIR"
