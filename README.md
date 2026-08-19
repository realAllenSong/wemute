# Wemute

Wemute 0.3 is a local-first desktop conversion workspace. Drop files in, choose
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

Wemute 0.3 begins M2 with one production-shaped AI vertical slice: on-device
background removal. The 4.4 MB U²-NetP model is not bundled or downloaded
silently. AI Tools shows its size and Apache-2.0 license first, then installs it
atomically with SHA-256 verification. Once installed, **Remove Background** joins
the same group and per-file output selectors as ordinary formats. Inference runs
in an isolated ONNX Runtime worker with Core ML preferred on supported Macs and
CPU fallback.

Core outputs include JPEG, PNG, WebP, HEIC, AVIF, TIFF, GIF, BMP; WAV, FLAC,
MP3, M4A/AAC, AIFF, OGG, Opus; and H.264/H.265 MP4, ProRes MOV, H.264 MKV,
VP9 WebM, and animated GIF. H.264/H.265 use VideoToolbox on macOS when it is
available.

## Tests

```bash
uv run pytest
uv run python -m wemute --smoke-test
```

## Web workspace

The first web edition lives in `apps/web`. It keeps the same quiet queue and
group/per-file override behavior, but limits its promise to browser-native image
work: PNG, JPEG and WebP conversion, resize, quality, rounded corners and batch
ZIP download. File bytes never leave the browser.

```bash
cd apps/web
npm install
npm run dev
```

Web verification runs with `npm run typecheck`, `npm test`, `npm run build` and
`npm run test:sites`.

## Build a development `.app`

```bash
./scripts/build-macos.sh
```

This alpha intentionally uses the FFmpeg installed on the current machine. A
public release must bundle a license-compatible runtime and its notices.

See [the web product strategy](docs/web-product-strategy.md) and
[the M2 architecture](docs/m2-architecture.md), plus
[the release gates](docs/release-gates.md), for the next distribution phase.
