import { FORMATS } from "./formats";
import { localePath, text, type Locale, type Text } from "./locale";
import type { Category, Tool } from "./tools";

/** The words a converter sentence can start from: "Convert [HEIC photos ▾] to …". */
export interface SourceDef {
  id: string;
  kind: Category | "any";
  label: Text;
}

export const SOURCES: SourceDef[] = [
  { id: "any", kind: "any", label: text("any file", "任意文件") },
  { id: "heic", kind: "image", label: text("HEIC photos", "HEIC 照片") },
  { id: "png", kind: "image", label: text("PNG images", "PNG 图片") },
  { id: "jpg", kind: "image", label: text("JPG images", "JPG 图片") },
  { id: "webp", kind: "image", label: text("WebP images", "WebP 图片") },
  { id: "avif", kind: "image", label: text("AVIF images", "AVIF 图片") },
  { id: "mov", kind: "video", label: text("MOV videos", "MOV 视频") },
  { id: "mp4", kind: "video", label: text("MP4 videos", "MP4 视频") },
  { id: "webm", kind: "video", label: text("WebM videos", "WebM 视频") },
  { id: "mkv", kind: "video", label: text("MKV videos", "MKV 视频") },
  { id: "wav", kind: "audio", label: text("WAV audio", "WAV 音频") },
  { id: "m4a", kind: "audio", label: text("M4A audio", "M4A 音频") },
  { id: "flac", kind: "audio", label: text("FLAC audio", "FLAC 音频") },
  { id: "mp3", kind: "audio", label: text("MP3 audio", "MP3 音频") },
];

/** The source word for tools that work on any file of a kind, e.g. "Compress [images] …". */
export const KIND_SOURCE: Record<Category, Text> = {
  image: text("images", "图片"),
  video: text("videos", "视频"),
  audio: text("audio", "音频"),
};

const SIZE_LABEL: Record<string, Text> = {
  "compress-image": text("a smaller size", "更小的体积"),
  "compress-image-to-50kb": text("under 50 KB", "50 KB"),
  "compress-image-to-100kb": text("under 100 KB", "100 KB"),
  "compress-image-to-200kb": text("under 200 KB", "200 KB"),
};

export interface PickerSource {
  id: string;
  kind: Category | "any";
  label: string;
}

export interface PickerLink {
  from: string;
  to: string;
  label: string;
  slug: string;
  href: string;
}

export interface PickerSize {
  slug: string;
  label: string;
  href: string;
}

/** Everything the converter's sentence needs to turn pill choices into tool pages. */
export interface PickerData {
  home: string;
  sources: PickerSource[];
  kindSource: Record<Category, string>;
  links: PickerLink[];
  sizes: PickerSize[];
}

/** Sources that at least one tool converts from, plus "any file". */
export function buildPicker(tools: Tool[], locale: Locale): PickerData {
  const links: PickerLink[] = [];
  for (const tool of tools) {
    const from = tool.from[0];
    if (!from || !tool.to || tool.from.length !== 1) continue;
    if (links.some((link) => link.from === from && link.to === tool.to)) continue;
    links.push({ from, to: tool.to, label: FORMATS[tool.to]?.name ?? tool.to.toUpperCase(), slug: tool.slug, href: localePath(locale, tool.slug) });
  }
  const sources = SOURCES.filter((source) => source.kind === "any" || links.some((link) => link.from === source.id)).map((source) => ({
    id: source.id,
    kind: source.kind,
    label: source.label[locale],
  }));
  const sizes = Object.keys(SIZE_LABEL)
    .filter((slug) => tools.some((tool) => tool.slug === slug))
    .map((slug) => ({ slug, label: SIZE_LABEL[slug][locale], href: localePath(locale, slug) }));
  return {
    home: localePath(locale),
    sources,
    kindSource: { image: KIND_SOURCE.image[locale], video: KIND_SOURCE.video[locale], audio: KIND_SOURCE.audio[locale] },
    links,
    sizes,
  };
}

export function targetsFor(picker: PickerData, source: string): PickerLink[] {
  return picker.links.filter((link) => link.from === source);
}

/** The tool page for a source, keeping the current target when that combination exists. */
export function linkFor(picker: PickerData, source: string, to?: string): PickerLink | undefined {
  const targets = targetsFor(picker, source);
  return targets.find((link) => link.to === to) ?? targets[0];
}

export function linkForSlug(picker: PickerData, slug: string): PickerLink | undefined {
  return picker.links.find((link) => link.slug === slug);
}
