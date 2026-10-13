import type { ImageOutput, ImagePreset } from "../data/tools";

export type EncodedImage = "jpeg" | "png" | "webp";

export interface ImageOptions {
  quality: NonNullable<ImagePreset["quality"]>;
  resize: NonNullable<ImagePreset["resize"]>;
  customWidth: number;
  cornerRadius: number;
  /** 0 disables the size target. */
  targetKB: number;
}

export const DEFAULT_IMAGE_OPTIONS: ImageOptions = {
  quality: "balanced",
  resize: "original",
  customWidth: 1600,
  cornerRadius: 0,
  targetKB: 0,
};

export const QUALITY: Record<ImageOptions["quality"], number> = {
  small: 0.66,
  balanced: 0.8,
  high: 0.92,
};

export const MIME: Record<EncodedImage, string> = {
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
};

export const EXTENSION: Record<EncodedImage, string> = {
  jpeg: "jpg",
  png: "png",
  webp: "webp",
};

const HEIC = /\.(heic|heif)$/i;

export function isHeic(file: File): boolean {
  return HEIC.test(file.name) || file.type === "image/heic" || file.type === "image/heif";
}

export function isImageFile(file: File): boolean {
  return file.type.startsWith("image/") || isHeic(file) || /\.(avif|bmp|gif|jpe?g|png|webp|tiff?)$/i.test(file.name);
}

/** Target dimensions; images are never enlarged. */
export function resolveDimensions(
  width: number,
  height: number,
  resize: ImageOptions["resize"],
  customWidth: number,
): { width: number; height: number } {
  if (width <= 0 || height <= 0) return { width: 1, height: 1 };
  const longest = Math.max(width, height);
  let scale = 1;
  if (resize === "half") scale = 0.5;
  if (resize === "long-1920") scale = Math.min(1, 1920 / longest);
  if (resize === "long-1080") scale = Math.min(1, 1080 / longest);
  if (resize === "custom") scale = Math.min(1, Math.max(1, customWidth) / width);
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

/**
 * Resolve "auto" and "keep" into a concrete encoder.
 * keep: same family as the source (HEIC/AVIF/other → JPG).
 * auto: like keep, but PNG becomes JPG — or WebP when it has transparency —
 *       because PNG cannot get meaningfully smaller without changing format.
 */
export function resolveImageOutput(output: ImageOutput, file: File, hasAlpha: boolean): EncodedImage {
  if (output === "jpeg" || output === "png" || output === "webp") return output;
  const name = file.name.toLowerCase();
  const type = file.type;
  const isJpeg = type === "image/jpeg" || /\.jpe?g$/.test(name);
  const isWebp = type === "image/webp" || name.endsWith(".webp");
  const isPng = type === "image/png" || name.endsWith(".png");
  if (isJpeg) return "jpeg";
  if (isWebp) return "webp";
  if (output === "keep" && isPng) return "png";
  return hasAlpha ? (output === "keep" ? "png" : "webp") : "jpeg";
}

// HEIC decoding is slow, and each file is decoded for its thumbnail and again
// for conversion, so keep the decoded PNG for the life of the File.
const decodedHeic = new WeakMap<File, Promise<Blob>>();

function decodeHeic(file: File): Promise<Blob> {
  let pending = decodedHeic.get(file);
  if (!pending) {
    pending = import("heic-to").then(({ heicTo }) => heicTo({ blob: file, type: "image/png" }));
    pending.catch(() => decodedHeic.delete(file));
    decodedHeic.set(file, pending);
  }
  return pending;
}

/** Decode any supported image, honouring EXIF orientation. */
export async function decodeImage(file: File): Promise<ImageBitmap> {
  try {
    const source = isHeic(file) ? await decodeHeic(file) : file;
    return await createImageBitmap(source, { imageOrientation: "from-image" });
  } catch {
    throw new Error(isHeic(file) ? "heic" : "decode");
  }
}

function roundedRect(context: CanvasRenderingContext2D, width: number, height: number, radius: number) {
  const r = Math.min(Math.max(0, radius), width / 2, height / 2);
  context.beginPath();
  context.moveTo(r, 0);
  context.arcTo(width, 0, width, height, r);
  context.arcTo(width, height, 0, height, r);
  context.arcTo(0, height, 0, 0, r);
  context.arcTo(0, 0, width, 0, r);
  context.closePath();
}

function drawToCanvas(
  bitmap: ImageBitmap,
  width: number,
  height: number,
  format: EncodedImage,
  cornerRadius: number,
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { alpha: format !== "jpeg" });
  if (!context) throw new Error("canvas");
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  if (format === "jpeg") {
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, width, height);
  }
  if (cornerRadius > 0) {
    roundedRect(context, width, height, cornerRadius);
    context.clip();
  }
  context.drawImage(bitmap, 0, 0, width, height);
  return canvas;
}

function toBlob(canvas: HTMLCanvasElement, format: EncodedImage, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) return reject(new Error("encode"));
        // Safari silently falls back to PNG for unsupported types.
        if (blob.type && blob.type !== MIME[format]) return reject(new Error("encode-unsupported"));
        resolve(blob);
      },
      MIME[format],
      format === "png" ? undefined : quality,
    );
  });
}

/** Sample the bitmap to see whether any pixel is translucent. */
export function hasTransparency(bitmap: ImageBitmap): boolean {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return false;
  context.drawImage(bitmap, 0, 0, size, size);
  const data = context.getImageData(0, 0, size, size).data;
  for (let index = 3; index < data.length; index += 4) if (data[index] < 250) return true;
  return false;
}

export interface ImageJob {
  file: File;
  output: ImageOutput;
  options: ImageOptions;
  onProgress?: (value: number) => void;
}

export interface ImageResult {
  blob: Blob;
  format: EncodedImage;
  width: number;
  height: number;
}

export async function convertImage({ file, output, options, onProgress }: ImageJob): Promise<ImageResult> {
  const bitmap = await decodeImage(file);
  onProgress?.(0.35);
  try {
    const needsAlphaCheck = output === "auto" || output === "keep";
    const alpha = needsAlphaCheck ? hasTransparency(bitmap) : false;
    const format = options.cornerRadius > 0 && output !== "webp" ? "png" : resolveImageOutput(output, file, alpha);
    let { width, height } = resolveDimensions(bitmap.width, bitmap.height, options.resize, options.customWidth);
    const radius = options.cornerRadius;

    if (options.targetKB > 0 && format !== "png") {
      const limit = options.targetKB * 1024;
      // Search quality first; shrink dimensions only when quality alone can't fit.
      for (let attempt = 0; attempt < 8; attempt += 1) {
        const canvas = drawToCanvas(bitmap, width, height, format, radius);
        let low = 0.3;
        let high = QUALITY[options.quality];
        let best: Blob | null = null;
        const first = await toBlob(canvas, format, high);
        if (first.size <= limit) best = first;
        else {
          for (let step = 0; step < 7; step += 1) {
            const middle = (low + high) / 2;
            const candidate = await toBlob(canvas, format, middle);
            if (candidate.size <= limit) {
              best = candidate;
              low = middle;
            } else high = middle;
          }
        }
        onProgress?.(0.4 + attempt * 0.07);
        if (best) return { blob: best, format, width, height };
        width = Math.max(1, Math.round(width * 0.82));
        height = Math.max(1, Math.round(height * 0.82));
      }
      throw new Error("target");
    }

    const canvas = drawToCanvas(bitmap, width, height, format, radius);
    onProgress?.(0.7);
    const blob = await toBlob(canvas, format, QUALITY[options.quality]);
    return { blob, format, width, height };
  } finally {
    bitmap.close();
  }
}

/** Small preview for the queue row. */
export async function thumbnail(file: File, size = 112): Promise<{ url: string; width: number; height: number }> {
  const bitmap = await decodeImage(file);
  try {
    const scale = Math.min(1, size / Math.min(bitmap.width, bitmap.height));
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, width, height);
    const blob = await toBlob(canvas, "jpeg", 0.8).catch(() => toBlob(canvas, "png", 1));
    return { url: URL.createObjectURL(blob), width: bitmap.width, height: bitmap.height };
  } finally {
    bitmap.close();
  }
}
