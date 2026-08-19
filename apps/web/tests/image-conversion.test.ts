import { describe, expect, it } from "vitest";
import { resolveDimensions } from "../src/lib/image-conversion";

describe("resize rules", () => {
  it("keeps original dimensions by default", () => {
    expect(resolveDimensions(3024, 4032, "original", 1920)).toEqual({ width: 3024, height: 4032 });
  });

  it("scales proportionally to fifty percent", () => {
    expect(resolveDimensions(3024, 4032, "half", 1920)).toEqual({ width: 1512, height: 2016 });
  });

  it("does not upscale a small image for the longest-edge preset", () => {
    expect(resolveDimensions(1280, 720, "long-1920", 1920)).toEqual({ width: 1280, height: 720 });
  });

  it("caps the longest edge at 1920 pixels", () => {
    expect(resolveDimensions(3840, 2160, "long-1920", 1920)).toEqual({ width: 1920, height: 1080 });
  });

  it("uses custom width while preserving aspect ratio", () => {
    expect(resolveDimensions(2400, 1600, "custom", 1200)).toEqual({ width: 1200, height: 800 });
  });
});
