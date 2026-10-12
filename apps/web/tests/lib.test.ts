import { describe, expect, it } from "vitest";
import { outputName, sizeDelta, uniqueNames, formatBytes } from "../src/lib/files";
import { resolveDimensions, resolveImageOutput } from "../src/lib/image";
import { canRemuxToMp4, parseProbe, planMedia } from "../src/lib/media";
import { formatDuration } from "../src/lib/preview";

const file = (name: string, type = "") => new File([new Uint8Array(1)], name, { type });

describe("image sizing", () => {
  it("never enlarges an image", () => {
    expect(resolveDimensions(800, 600, "long-1920", 0)).toEqual({ width: 800, height: 600 });
    expect(resolveDimensions(800, 600, "custom", 4000)).toEqual({ width: 800, height: 600 });
  });

  it("fits the longest edge and keeps proportions", () => {
    expect(resolveDimensions(4000, 3000, "long-1920", 0)).toEqual({ width: 1920, height: 1440 });
    expect(resolveDimensions(3000, 4000, "long-1080", 0)).toEqual({ width: 810, height: 1080 });
    expect(resolveDimensions(1000, 500, "half", 0)).toEqual({ width: 500, height: 250 });
  });
});

describe("image output", () => {
  it("keeps JPG and WebP families", () => {
    expect(resolveImageOutput("auto", file("a.jpg", "image/jpeg"), false)).toBe("jpeg");
    expect(resolveImageOutput("keep", file("a.webp", "image/webp"), true)).toBe("webp");
  });

  it("compresses PNG to JPG, or WebP when it has transparency", () => {
    expect(resolveImageOutput("auto", file("a.png", "image/png"), false)).toBe("jpeg");
    expect(resolveImageOutput("auto", file("a.png", "image/png"), true)).toBe("webp");
  });

  it("keep leaves PNG as PNG and turns HEIC into JPG", () => {
    expect(resolveImageOutput("keep", file("a.png", "image/png"), false)).toBe("png");
    expect(resolveImageOutput("keep", file("IMG_1.HEIC"), false)).toBe("jpeg");
  });
});

describe("file names", () => {
  it("adds a suffix only when the extension is unchanged", () => {
    expect(outputName("IMG_1.HEIC", "jpg")).toBe("IMG_1.jpg");
    expect(outputName("photo.jpg", "jpg")).toBe("photo-wemute.jpg");
  });

  it("makes ZIP entries unique", () => {
    expect(uniqueNames(["a.jpg", "A.jpg", "a.jpg", "b.jpg"])).toEqual(["a.jpg", "A (2).jpg", "a (3).jpg", "b.jpg"]);
  });

  it("formats sizes and deltas", () => {
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(sizeDelta(100, 27)).toEqual({ label: "−73%", smaller: true });
    expect(sizeDelta(100, 134).label).toBe("+34%");
    expect(sizeDelta(100, 100).label).toBe("");
    expect(formatDuration(3725)).toBe("1:02:05");
    expect(formatDuration(65)).toBe("1:05");
  });
});

describe("media planning", () => {
  const log = [
    "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'in.mov':",
    "  Duration: 00:01:02.50, start: 0.000000, bitrate: 9000 kb/s",
    "  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1920x1080",
    "  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo",
  ].join("\n");

  it("reads codecs and duration", () => {
    expect(parseProbe(log)).toEqual({ video: "h264", audio: "aac", duration: 62.5 });
  });

  it("remuxes H.264 into MP4 without re-encoding", () => {
    const probe = parseProbe(log);
    expect(canRemuxToMp4(probe)).toBe(true);
    const plan = planMedia("in.mov", "out.mp4", "mp4", "convert", probe);
    expect(plan.args).toContain("copy");
    expect(plan.args).not.toContain("libx264");
  });

  it("re-encodes HEVC and always re-encodes when compressing", () => {
    expect(canRemuxToMp4({ video: "hevc", audio: "aac" })).toBe(false);
    const plan = planMedia("in.mov", "out.mp4", "mp4", "compress", parseProbe(log));
    expect(plan.args).toContain("libx264");
    expect(plan.args.join(" ")).toContain("min(720,ih)");
  });

  it("builds GIF and audio extraction commands", () => {
    const gif = planMedia("in.mp4", "out.gif", "gif", "gif", {}, { start: 2, length: 4, width: 480, fps: 12 });
    expect(gif.args.slice(0, 7)).toEqual(["-hide_banner", "-y", "-ss", "2", "-t", "4", "-i"]);
    expect(gif.args.join(" ")).toContain("palettegen");
    const mp3 = planMedia("in.mp4", "out.mp3", "mp3", "convert", {});
    expect(mp3.args).toEqual(expect.arrayContaining(["-vn", "libmp3lame"]));
  });
});
