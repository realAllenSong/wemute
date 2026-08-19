export type OutputFormat = "png" | "jpeg" | "webp";

export type QualityPreset = "small" | "balanced" | "high";

export type ResizePreset = "original" | "half" | "long-1920" | "custom";

export type QueueStatus = "preparing" | "ready" | "converting" | "done" | "error";

export interface ConversionOptions {
  quality: QualityPreset;
  resize: ResizePreset;
  customWidth: number;
  cornerRadius: number;
}

export interface QueueImage {
  id: string;
  file: File;
  sourceUrl: string;
  width: number;
  height: number;
  targetFormat: OutputFormat;
  status: QueueStatus;
  progress: number;
  outputBlob?: Blob;
  outputName?: string;
  error?: string;
}

export type Locale = "en" | "zh";
