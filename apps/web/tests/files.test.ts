import { describe, expect, it } from "vitest";
import { formatBytes, outputNameFor, uniqueOutputNames } from "../src/lib/files";

describe("file helpers", () => {
  it("formats byte sizes for compact queue metadata", () => {
    expect(formatBytes(2_420_000)).toBe("2.3 MB");
    expect(formatBytes(512)).toBe("1 KB");
  });

  it("replaces the source extension with the requested output extension", () => {
    expect(outputNameFor("Portrait.HEIC", "jpeg")).toBe("Portrait.jpg");
    expect(outputNameFor("image", "webp")).toBe("image.webp");
  });

  it("deconflicts output names without changing the first file", () => {
    expect(uniqueOutputNames(["image.webp", "image.webp", "image.webp"]))
      .toEqual(["image.webp", "image 2.webp", "image 3.webp"]);
  });
});
