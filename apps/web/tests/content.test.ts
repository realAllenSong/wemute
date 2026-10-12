import { describe, expect, it } from "vitest";
import { FORMATS } from "../src/data/formats";
import { LEGAL } from "../src/data/site";
import { TOOLS, TOOL_BY_SLUG } from "../src/data/tools";
import { UI } from "../src/data/ui";

const LOCALES = ["en", "zh"] as const;

describe("tool content", () => {
  it("has unique slugs and titles", () => {
    expect(new Set(TOOLS.map((tool) => tool.slug)).size).toBe(TOOLS.length);
    for (const locale of LOCALES) {
      const titles = TOOLS.map((tool) => tool.metaTitle[locale]);
      expect(new Set(titles).size).toBe(titles.length);
    }
  });

  it("is complete in both languages", () => {
    for (const tool of TOOLS) {
      for (const locale of LOCALES) {
        for (const value of [tool.name, tool.h1, tool.metaTitle, tool.metaDescription, tool.answer]) {
          expect(value[locale].trim().length, `${tool.slug} ${locale}`).toBeGreaterThan(2);
        }
        expect(tool.steps.length).toBeGreaterThanOrEqual(3);
        expect(tool.faqs.length).toBeGreaterThanOrEqual(3);
        for (const faq of tool.faqs) expect(faq.a[locale].length).toBeGreaterThan(20);
      }
    }
  });

  it("keeps meta titles and descriptions within search snippet limits", () => {
    for (const tool of TOOLS) {
      expect(tool.metaTitle.en.length, tool.slug).toBeLessThanOrEqual(70);
      expect(tool.metaDescription.en.length, tool.slug).toBeLessThanOrEqual(170);
    }
  });

  it("links only to tools that exist", () => {
    for (const tool of TOOLS) for (const slug of tool.related) expect(TOOL_BY_SLUG.has(slug), `${tool.slug} → ${slug}`).toBe(true);
  });

  it("offers its default output and knows its formats", () => {
    for (const tool of TOOLS) {
      expect(tool.outputs).toContain(tool.output);
      for (const format of [...tool.from, ...(tool.to ? [tool.to] : [])]) expect(FORMATS[format], format).toBeDefined();
    }
  });

  it("never collides with legal pages", () => {
    for (const page of LEGAL) expect(TOOL_BY_SLUG.has(page.slug)).toBe(false);
  });
});

describe("interface strings", () => {
  it("translates every key", () => {
    expect(Object.keys(UI.zh).sort()).toEqual(Object.keys(UI.en).sort());
  });
});
