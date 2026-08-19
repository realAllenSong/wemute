import type { OutputFormat } from "../types";

const FORMAT_EXTENSIONS: Record<OutputFormat, string> = {
  png: "png",
  jpeg: "jpg",
  webp: "webp",
};

export function isImageFile(file: File): boolean {
  return file.type.startsWith("image/") || /\.(avif|gif|heic|heif|jpe?g|png|tiff?|webp)$/i.test(file.name);
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 KB";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

export function outputNameFor(sourceName: string, format: OutputFormat): string {
  const stem = sourceName.replace(/\.[^/.]+$/, "") || "image";
  return `${stem}.${FORMAT_EXTENSIONS[format]}`;
}

export function uniqueOutputNames(names: string[]): string[] {
  const used = new Set<string>();
  return names.map((name) => {
    if (!used.has(name.toLocaleLowerCase())) {
      used.add(name.toLocaleLowerCase());
      return name;
    }

    const dot = name.lastIndexOf(".");
    const stem = dot > 0 ? name.slice(0, dot) : name;
    const extension = dot > 0 ? name.slice(dot) : "";
    let suffix = 2;
    let candidate = `${stem} ${suffix}${extension}`;
    while (used.has(candidate.toLocaleLowerCase())) {
      suffix += 1;
      candidate = `${stem} ${suffix}${extension}`;
    }
    used.add(candidate.toLocaleLowerCase());
    return candidate;
  });
}

export function formatLabel(format: OutputFormat): string {
  return format === "jpeg" ? "JPEG" : format.toUpperCase();
}
