# Wemute

Wemute 0.2 is a local-first desktop conversion workspace. Drop files in, choose
what they should become, and convert them without uploading anything.

## Run on macOS

Requirements: macOS 14+, Apple Silicon, `uv`, and FFmpeg/FFprobe on `PATH`.

```bash
uv sync --dev
uv run wemute
```

The current alpha supports image conversion through an isolated Pillow worker
and audio/video conversion through FFmpeg. It includes mixed-file queues, drag
and drop, per-file output formats, safe non-overwriting outputs, cancellation,
retry, real thumbnails, Quick Look, and local queue recovery.

Each image/audio/video group also has an **All → format** selector for one-action
batch changes while every row remains independently customizable. Image jobs
support original/50%/long-edge resize presets, three quality levels and 24/64 px
rounded corners from a compact Image Options panel.

Core outputs include JPEG, PNG, WebP, HEIC, AVIF, TIFF, GIF, BMP; WAV, FLAC,
MP3, M4A/AAC, AIFF, OGG, Opus; and H.264/H.265 MP4, ProRes MOV, H.264 MKV,
VP9 WebM, and animated GIF. H.264/H.265 use VideoToolbox on macOS when it is
available.

## Tests

```bash
uv run pytest
uv run python -m wemute --smoke-test
```

## Build a development `.app`

```bash
./scripts/build-macos.sh
```

This alpha intentionally uses the FFmpeg installed on the current machine. A
public release must bundle a license-compatible runtime and its notices.

See [the web product strategy](docs/web-product-strategy.md) and
[the release gates](docs/release-gates.md) for the next distribution phase.
