import type { ConversionOptions, Locale, OutputFormat } from "./types";

export type ToolSlug = "convert-image" | "compress-image" | "resize-image" | "round-corners";

export interface ToolDefinition {
  slug: ToolSlug;
  path: string;
  icon: "convert" | "compress" | "resize" | "corners";
  title: Record<Locale, string>;
  shortTitle: Record<Locale, string>;
  description: Record<Locale, string>;
  dropHint: Record<Locale, string>;
  options: ConversionOptions;
  format: OutputFormat;
}

export const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    slug: "convert-image",
    path: "/tools/convert-image",
    icon: "convert",
    title: { en: "Convert images in one clean batch", zh: "一次转换整批图片" },
    shortTitle: { en: "Convert images", zh: "图片转换" },
    description: {
      en: "Turn PNG, JPEG, WebP and supported HEIC images into the format you need — without sending them anywhere.",
      zh: "将 PNG、JPEG、WebP 和支持的 HEIC 图片批量转成所需格式，全程无需上传。",
    },
    dropHint: { en: "Drop images to choose an output format", zh: "拖入图片，然后选择输出格式" },
    options: { quality: "balanced", resize: "original", customWidth: 1920, cornerRadius: 0 },
    format: "webp",
  },
  {
    slug: "compress-image",
    path: "/tools/compress-image",
    icon: "compress",
    title: { en: "Make images lighter, not worse", zh: "缩小体积，保留质感" },
    shortTitle: { en: "Compress images", zh: "图片压缩" },
    description: {
      en: "Reduce image size locally with a sensible quality preset. Compare the result before you keep it.",
      zh: "使用合适的质量预设在本机压缩图片，并清楚查看压缩前后的体积。",
    },
    dropHint: { en: "Drop images to compress them locally", zh: "拖入图片，在本机完成压缩" },
    options: { quality: "small", resize: "original", customWidth: 1920, cornerRadius: 0 },
    format: "webp",
  },
  {
    slug: "resize-image",
    path: "/tools/resize-image",
    icon: "resize",
    title: { en: "Resize a whole set at once", zh: "一次调整整组图片尺寸" },
    shortTitle: { en: "Resize images", zh: "调整尺寸" },
    description: {
      en: "Scale images by half, fit a long edge, or use a precise custom width while keeping proportions intact.",
      zh: "按比例缩小、限制最长边或输入精确宽度，同时保持图片比例不变。",
    },
    dropHint: { en: "Drop images to resize them together", zh: "拖入图片，统一调整尺寸" },
    options: { quality: "balanced", resize: "half", customWidth: 1920, cornerRadius: 0 },
    format: "webp",
  },
  {
    slug: "round-corners",
    path: "/tools/round-corners",
    icon: "corners",
    title: { en: "Give images genuinely clean corners", zh: "给图片加上真正干净的圆角" },
    shortTitle: { en: "Round corners", zh: "图片圆角" },
    description: {
      en: "Create transparent rounded corners in one batch, with no editor and no upload step.",
      zh: "无需打开编辑器，也无需上传，一次为整批图片生成透明圆角。",
    },
    dropHint: { en: "Drop images to add transparent corners", zh: "拖入图片，添加透明圆角" },
    options: { quality: "balanced", resize: "original", customWidth: 1920, cornerRadius: 32 },
    format: "png",
  },
];

export function toolFromPath(pathname: string): ToolDefinition | undefined {
  return TOOL_DEFINITIONS.find((tool) => tool.path === pathname.replace(/\/$/, ""));
}

export function safePath(pathname: string): string {
  return toolFromPath(pathname)?.path ?? "/";
}
