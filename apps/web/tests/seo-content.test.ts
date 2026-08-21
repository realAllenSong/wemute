import { describe, expect, it } from "vitest";
import { INDEXABLE_PATHS, metadataForPath, structuredDataForPath } from "../src/site-content.js";

describe("public search content", () => {
  it("gives every indexable route unique metadata", () => {
    const metadata = INDEXABLE_PATHS.map(metadataForPath);
    expect(new Set(metadata.map((page) => page.title)).size).toBe(INDEXABLE_PATHS.length);
    expect(new Set(metadata.map((page) => page.description)).size).toBe(INDEXABLE_PATHS.length);
  });

  it("describes tools as free browser applications without invented ratings", () => {
    const schema = structuredDataForPath("/tools/compress-image", "https://wemute.test");
    const serialized = JSON.stringify(schema);
    expect(serialized).toContain("WebApplication");
    expect(serialized).toContain('"price":"0"');
    expect(serialized).toContain("BreadcrumbList");
    expect(serialized).not.toContain("aggregateRating");
  });

  it("keeps unknown routes on the home metadata", () => {
    expect(metadataForPath("/missing").path).toBe("/");
  });
});
