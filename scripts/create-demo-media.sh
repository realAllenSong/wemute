#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
REFERENCE="$PROJECT_DIR/design/reference/wemute-queue-target.png"
OUTPUT_DIR="$PROJECT_DIR/artifacts/demo-media"

mkdir -p "$OUTPUT_DIR"

ffmpeg -hide_banner -loglevel error -y -i "$REFERENCE" -vf "crop=140:98:62:211,scale=700:490" "$OUTPUT_DIR/portrait.jpg"
sips -s format heic "$OUTPUT_DIR/portrait.jpg" --out "$OUTPUT_DIR/Portrait.heic" >/dev/null

ffmpeg -hide_banner -loglevel error -y -f lavfi -i "sine=frequency=220:duration=3" -c:a pcm_s24le "$OUTPUT_DIR/Field Recording.wav"

make_video() {
  local name="$1"
  local crop="$2"
  local still="$OUTPUT_DIR/${name}.jpg"
  ffmpeg -hide_banner -loglevel error -y -i "$REFERENCE" -vf "$crop,scale=960:540" "$still"
  ffmpeg -hide_banner -loglevel error -y -loop 1 -i "$still" -f lavfi -i "anullsrc=r=48000:cl=stereo" \
    -t 2 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$OUTPUT_DIR/${name}.mov"
}

make_video "Product Demo" "crop=140:93:62:568"
make_video "Surf Session" "crop=140:95:62:684"
make_video "City Timelapse" "crop=140:92:62:800"

echo "$OUTPUT_DIR"
