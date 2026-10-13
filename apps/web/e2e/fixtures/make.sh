#!/usr/bin/env bash
# Generates small, real sample files for the end-to-end suite.
# Usage: make.sh <output-dir>
# Needs ffmpeg (libx264, libx265, libvpx-vp9, libopus, libmp3lame) and macOS `sips`.
# Optional formats that cannot be produced are listed in <output-dir>/skipped.txt
# as "<file>: <reason>" so the tests can skip them with that reason.
set -euo pipefail

out="${1:?usage: make.sh <output-dir>}"
mkdir -p "$out"
cd "$out"
: > skipped.txt

ff() { ffmpeg -hide_banner -loglevel error -y "$@"; }
has_encoder() { ffmpeg -hide_banner -encoders 2>/dev/null | grep -qE "^ [A-Z.]{6} $1 "; }
skip() { echo "$1: $2" >> skipped.txt; echo "skipped $1 ($2)" >&2; }

# ── images ──────────────────────────────────────────────────────────────
# 2000×1500 photographic-ish JPEG.
ff -f lavfi -i "mandelbrot=s=2000x1500:end_pts=1" -frames:v 1 -vf "noise=alls=12:allf=t" -q:v 3 photo.jpg

# 800×600 PNG: left half opaque test card, right half fully transparent.
ff -f lavfi -i "testsrc2=s=800x600:d=1" -frames:v 1 \
  -vf "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(X,400),255,0)'" shot.png

# WebP with the same transparency as shot.png.
if has_encoder libwebp; then
  ff -i shot.png -c:v libwebp -quality 80 image.webp
elif command -v cwebp > /dev/null; then
  cwebp -quiet -q 80 -exact shot.png -o image.webp
else
  skip image.webp "neither ffmpeg libwebp nor cwebp is available"
fi

# AVIF still image.
avif_ffmpeg() {
  local encoder
  for encoder in libsvtav1 libaom-av1; do
    has_encoder "$encoder" || continue
    ff -i photo.jpg -vf "scale=1200:900,format=yuv420p" -frames:v 1 -c:v "$encoder" image.avif > /dev/null 2>&1 && return 0
  done
  return 1
}
if avif_ffmpeg; then
  :
elif command -v avifenc > /dev/null && avifenc -q 60 photo.jpg image.avif > /dev/null 2>&1; then
  :
else
  rm -f image.avif
  skip image.avif "local ffmpeg cannot encode AVIF (no libsvtav1/libaom-av1) and avifenc is missing"
fi

# HEIC like an iPhone photo.
if command -v sips > /dev/null; then
  ff -i photo.jpg -vf scale=1600:1200 -q:v 3 heic-source.jpg
  sips -s format heic heic-source.jpg --out iphone.heic > /dev/null
  rm -f heic-source.jpg
else
  skip iphone.heic "macOS sips is not available"
fi

# ~5 MB JPEG so that 50/100/200 KB targets are real work.
ff -f lavfi -i "mandelbrot=s=3000x2250:end_pts=1" -frames:v 1 -vf "noise=alls=16:allf=t" -q:v 3 large.jpg

# ── video ───────────────────────────────────────────────────────────────
video_src=(-f lavfi -i "testsrc2=s=1280x720:r=30:d=3" -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=3")
small_src=(-f lavfi -i "testsrc2=s=640x360:r=30:d=3" -f lavfi -i "sine=frequency=660:sample_rate=48000:duration=3")

# High bitrate so compression has something to remove.
ff "${video_src[@]}" -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -c:a aac -b:a 128k -shortest -movflags +faststart clip.mp4
ff "${small_src[@]}" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 128k -shortest clip.mov
ff "${small_src[@]}" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 128k -shortest movie.mkv
ff "${small_src[@]}" -c:v libx265 -preset ultrafast -crf 26 -pix_fmt yuv420p -tag:v hvc1 -x265-params log-level=error \
  -c:a aac -b:a 128k -shortest hevc.mov
ff "${small_src[@]}" -c:v libvpx-vp9 -deadline realtime -cpu-used 8 -b:v 800k -c:a libopus -b:a 96k -shortest rec.webm

# ── audio ───────────────────────────────────────────────────────────────
tone=(-f lavfi -i "sine=frequency=523:sample_rate=44100:duration=3" -ac 2)
ff "${tone[@]}" -c:a pcm_s16le song.wav
ff "${tone[@]}" -c:a aac -b:a 128k voice.m4a
ff "${tone[@]}" -c:a flac track.flac
ff "${tone[@]}" -c:a libmp3lame -q:a 4 song.mp3

# ── edge cases ──────────────────────────────────────────────────────────
# Already squeezed hard: re-encoding it at "balanced" would only make it bigger.
ff -i photo.jpg -q:v 31 tiny.jpg
# H.264 with Opus audio, which MP4 players don't take: only the audio needs work.
ff "${small_src[@]}" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a libopus -b:a 96k -shortest movie-opus.mkv
# Picture only, nothing to extract as audio.
ff -f lavfi -i "testsrc2=s=640x360:r=30:d=3" -c:v libx264 -preset veryfast -pix_fmt yuv420p silent.mp4

# ── not convertible ─────────────────────────────────────────────────────
printf 'Just some notes, not media.\n' > notes.txt
# A real PNG signature followed by garbage: looks like a PNG, cannot be decoded.
{ printf '\x89PNG\r\n\x1a\n'; head -c 4096 /dev/urandom; } > broken.png
# An ISO-BMFF "ftypheic" header followed by garbage.
{ printf '\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic'; head -c 4096 /dev/urandom; } > broken.heic

touch .complete
