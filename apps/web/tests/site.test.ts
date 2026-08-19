import { describe, expect, it } from "vitest";
import { safePath, toolFromPath, TOOL_DEFINITIONS } from "../src/site";

describe("web tool routes", () => {
  it("exposes only the focused tools implemented in the browser", () => {
    expect(TOOL_DEFINITIONS.map((tool) => tool.slug)).toEqual([
      "convert-image",
      "compress-image",
      "resize-image",
      "round-corners",
    ]);
  });

  it("resolves supported routes and sends unknown paths home", () => {
    expect(toolFromPath("/tools/resize-image/")?.options.resize).toBe("half");
    expect(safePath("/tools/round-corners")).toBe("/tools/round-corners");
    expect(safePath("/not-a-tool")).toBe("/");
  });

  it("uses a transparent format for rounded corners", () => {
    expect(toolFromPath("/tools/round-corners")?.format).toBe("png");
    expect(toolFromPath("/tools/round-corners")?.options.cornerRadius).toBeGreaterThan(0);
  });
});
