import { describe, expect, it } from "vitest";
import { FORMATS } from "../src/data/formats";
import { LEGAL } from "../src/data/site";
import { MAC_PAGES } from "../src/data/mac-pages";
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

describe("Mac app pages", () => {
  it("never collide with tools or legal pages", () => {
    for (const page of MAC_PAGES) {
      expect(TOOL_BY_SLUG.has(page.slug), page.slug).toBe(false);
      expect(LEGAL.some((legal) => legal.slug === (page.slug as string)), page.slug).toBe(false);
    }
  });

  it("are complete in both languages, with tables that line up", () => {
    for (const page of MAC_PAGES) {
      expect(page.metaTitle.en.length, page.slug).toBeLessThanOrEqual(70);
      expect(page.metaDescription.en.length, page.slug).toBeLessThanOrEqual(170);
      expect(page.faqs.length).toBeGreaterThanOrEqual(3);
      for (const row of page.compare.rows) expect(row.cells.length, `${page.slug} ${row.label.en}`).toBe(page.compare.columns.length);
      for (const locale of LOCALES) for (const value of [page.name, page.h1, page.answer]) expect(value[locale].trim().length).toBeGreaterThan(2);
    }
  });
});

describe("interface strings", () => {
  it("translates every key", () => {
    expect(Object.keys(UI.zh).sort()).toEqual(Object.keys(UI.en).sort());
  });
});
