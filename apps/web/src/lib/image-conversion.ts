import type { ConversionOptions, OutputFormat, ResizePreset } from "../types";

export const MIME_BY_FORMAT: Record<OutputFormat, string> = {
  png: "image/png",
  jpeg: "image/jpeg",
  webp: "image/webp",
};

export const QUALITY_BY_PRESET = {
  small: 0.62,
  balanced: 0.82,
  high: 0.94,
} as const;

export function resolveDimensions(
  width: number,
  height: number,
  resize: ResizePreset,
  customWidth: number,
): { width: number; height: number } {
  if (width <= 0 || height <= 0) return { width: 1, height: 1 };

  let scale = 1;
  if (resize === "half") scale = 0.5;
  if (resize === "long-1920") scale = Math.min(1, 1920 / Math.max(width, height));
  if (resize === "custom") scale = Math.min(1, Math.max(1, customWidth) / width);

  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

function roundedRectPath(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  radius: number,
): void {
  const safeRadius = Math.min(Math.max(0, radius), width / 2, height / 2);
  context.beginPath();
  context.moveTo(safeRadius, 0);
  context.lineTo(width - safeRadius, 0);
  context.arcTo(width, 0, width, safeRadius, safeRadius);
  context.lineTo(width, height - safeRadius);
  context.arcTo(width, height, width - safeRadius, height, safeRadius);
  context.lineTo(safeRadius, height);
  context.arcTo(0, height, 0, height - safeRadius, safeRadius);
  context.lineTo(0, safeRadius);
  context.arcTo(0, 0, safeRadius, 0, safeRadius);
  context.closePath();
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error(`This browser cannot export ${type}.`));
          return;
        }
        if (blob.type && blob.type !== type) {
          reject(new Error(`This browser does not support ${type} export.`));
          return;
        }
        resolve(blob);
      },
      type,
      quality,
    );
  });
}

export async function convertImage(
  file: File,
  sourceWidth: number,
  sourceHeight: number,
  format: OutputFormat,
  options: ConversionOptions,
): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  try {
    const sourceW = sourceWidth || bitmap.width;
    const sourceH = sourceHeight || bitmap.height;
    const dimensions = resolveDimensions(sourceW, sourceH, options.resize, options.customWidth);
    const canvas = document.createElement("canvas");
    canvas.width = dimensions.width;
    canvas.height = dimensions.height;
    const context = canvas.getContext("2d", { alpha: format !== "jpeg" });
    if (!context) throw new Error("Canvas rendering is unavailable in this browser.");

    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    if (format === "jpeg") {
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, dimensions.width, dimensions.height);
    }

    if (options.cornerRadius > 0) {
      roundedRectPath(context, dimensions.width, dimensions.height, options.cornerRadius);
      context.clip();
    }

    context.drawImage(bitmap, 0, 0, dimensions.width, dimensions.height);
    return await canvasToBlob(canvas, MIME_BY_FORMAT[format], QUALITY_BY_PRESET[options.quality]);
  } finally {
    bitmap.close();
  }
}

export async function probeImage(file: File): Promise<{ width: number; height: number }> {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  try {
    return { width: bitmap.width, height: bitmap.height };
  } finally {
    bitmap.close();
  }
}
