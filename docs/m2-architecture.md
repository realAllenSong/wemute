# Wemute M2: optional on-device intelligence

M2 uses the same output-choice model as conversion. Installing an AI package adds
an outcome such as **Remove Background** to the existing **All →** and per-file
menus. It does not add a second queue, navigation hierarchy or permanent panel.

## Shipped in 0.3

The first complete slice is fast local background removal:

- The bundled catalog describes the U²-NetP artifact, version, exact size,
  SHA-256 and Apache-2.0 license.
- AI Tools asks for an explicit download action after showing the 4.4 MB size and
  license. No model is bundled or silently fetched.
- Downloads use a `.part` file, reject oversize/truncated data, verify SHA-256,
  then atomically activate a version. Cancellation and checksum failures delete
  the partial file.
- Installed model versions remain addressable so a future catalog can activate a
  previous version without redownloading it.
- Inference runs in a separate process. ONNX Runtime prefers its Core ML provider
  with a persistent compiled-model cache, then falls back to CPU.
- The conversion queue retains cancellation, crash isolation, temporary output
  cleanup and non-overwriting final names for the AI path.

The model is downloaded from the official rembg release asset while the original
U²-Net project provides the model/source license. Wemute verifies the stronger
SHA-256 value in its own manifest rather than disabling upstream checks. Sources:
[rembg](https://github.com/danielgatis/rembg),
[U²-Net](https://github.com/xuebinqin/U-2-Net), and
[ONNX Runtime Core ML](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html).

## Next packages

The order is intentionally conservative:

1. **Background Removal · High Quality:** BiRefNet General Lite, approximately
   224 MB, as a second explicit quality choice rather than replacing the fast
   4.4 MB default.
2. **Upscale 2×/4×:** Real-ESRGAN Photo and Illustration presets. The current
   upstream macOS NCNN bundle is useful for local alpha testing, but public builds
   must compile and sign the helper and include BSD-3-Clause notices.
3. **Erase Object:** brush mask plus the Apache-2.0 OpenCV LaMa ONNX model. The UI
   will state that it is for content the user has the right to edit.
4. **Separate Vocals:** two-track output by default and four stems in Advanced.
   It remains blocked from public distribution until each selected weight has a
   clear commercial license; a MIT runtime does not license third-party weights.

Official implementation sources:
[BiRefNet](https://github.com/ZhengPeng7/BiRefNet),
[Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN),
[OpenCV LaMa](https://huggingface.co/opencv/inpainting_lama), and
[MLX Audio Separator](https://github.com/ssmall256/mlx-audio-separator).

## Boundary

The public application never accepts arbitrary model URLs or arbitrary worker
commands. Catalog entries are allow-listed at build time, and workers receive
only the action, source, destination, verified local model path and a small typed
option object. Future archive packages must also reject path traversal and
escaping symlinks before extraction.
