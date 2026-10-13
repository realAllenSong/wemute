import { describe, expect, it } from "vitest";
import { buildPicker, linkFor, linkForSlug, targetsFor } from "../src/data/picker";
import { HOME } from "../src/data/site";
import { TOOLS, TOOL_BY_SLUG } from "../src/data/tools";

const en = buildPicker(TOOLS, "en");
const zh = buildPicker(TOOLS, "zh");

const targets = (source: string) => targetsFor(en, source).map((link) => link.to);

describe("sentence picker", () => {
  it("starts with any file, then only sources a tool converts from", () => {
    expect(en.sources[0]).toMatchObject({ id: "any", label: "any file" });
    expect(zh.sources[0].label).toBe("任意文件");
    expect(en.sources.map((source) => source.id)).toEqual(["any", "heic", "png", "jpg", "webp", "avif", "mov", "mp4", "webm", "mkv", "wav", "m4a", "flac", "mp3"]);
    for (const source of en.sources.slice(1)) expect(targets(source.id).length, source.id).toBeGreaterThan(0);
  });

  it("offers only targets that have a tool", () => {
    expect(targets("heic")).toEqual(["jpg", "png"]);
    expect(targets("png")).toEqual(["jpg", "webp"]);
    expect(targets("jpg")).toEqual(["png", "webp"]);
    expect(targets("mov")).toEqual(["mp4"]);
    expect(targets("mp4")).toEqual(["mp3", "gif"]);
    expect(targets("wav")).toEqual(["mp3"]);
    expect(targets("any")).toEqual([]);
  });

  it("maps every combination to an existing localized tool page", () => {
    for (const link of [...en.links, ...zh.links]) {
      const tool = TOOL_BY_SLUG.get(link.slug);
      expect(tool, link.slug).toBeDefined();
      expect(tool!.from[0]).toBe(link.from);
      expect(tool!.to).toBe(link.to);
    }
    expect(linkFor(en, "heic", "jpg")?.href).toBe("/heic-to-jpg");
    expect(linkFor(zh, "heic", "png")?.href).toBe("/zh/heic-to-png");
    expect(linkFor(zh, "mp4", "gif")?.href).toBe("/zh/video-to-gif");
    expect(zh.home).toBe("/zh");
  });

  it("keeps the target when switching source, falling back to the first target", () => {
    expect(linkFor(en, "png", "jpg")?.slug).toBe("png-to-jpg");
    expect(linkFor(en, "mov", "jpg")?.slug).toBe("mov-to-mp4");
    expect(linkFor(en, "any", "jpg")).toBeUndefined();
  });

  it("knows each conversion tool's own source and target", () => {
    for (const tool of TOOLS.filter((item) => item.from.length === 1 && item.to)) {
      expect(linkForSlug(en, tool.slug), tool.slug).toMatchObject({ from: tool.from[0], to: tool.to });
    }
  });

  it("links the size family to real pages", () => {
    expect(zh.sizes.map((size) => size.href)).toEqual(["/zh/compress-image", "/zh/compress-image-to-50kb", "/zh/compress-image-to-100kb", "/zh/compress-image-to-200kb"]);
  });
});

describe("home copy", () => {
  it("states the real number of tools", () => {
    expect(HOME.toolsTitle.en).toContain(String(TOOLS.length));
    expect(HOME.why[2].figure).toBe(String(TOOLS.length));
  });

  it("lists popular image tools that exist", () => {
    for (const slug of HOME.popularImage) expect(TOOL_BY_SLUG.get(slug)?.category, slug).toBe("image");
  });
});
