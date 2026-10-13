import type { Page } from "@playwright/test";
import type { Output as ToolOutput, Tool } from "../src/data/tools";
import { audioStream, expect, ffprobe, fixture, pixel, sizeOf, streamHash, videoStream, openPill, type FixtureName, type Output } from "./helpers";

export interface ToolCase {
  fixtures: FixtureName[];
  /** Runs on the empty page, before files are added. */
  before?: (page: Page) => Promise<void>;
  /** Runs once the files are read, before Convert (video tools only). */
  configure?: (page: Page) => Promise<void>;
  verify: (outputs: Output[]) => void;
}

// ── assertions on output files ──────────────────────────────────────────

const CODEC: Partial<Record<ToolOutput, string>> = { jpeg: "mjpeg", png: "png", webp: "webp", gif: "gif", mp3: "mp3", wav: "pcm_s16le", m4a: "aac" };
const EXT: Partial<Record<ToolOutput, string>> = { jpeg: "jpg", png: "png", webp: "webp", gif: "gif", mp3: "mp3", wav: "wav", m4a: "m4a", mp4: "mp4" };

function one(outputs: Output[], name?: string): Output {
  if (name) {
    const found = outputs.find((output) => output.name === name);
    expect(found, `output ${name} in ${outputs.map((output) => output.name).join(", ")}`).toBeDefined();
    return found!;
  }
  expect(outputs).toHaveLength(1);
  return outputs[0];
}

export function expectImage(output: Output, format: "jpeg" | "png" | "webp", size?: { width: number; height: number }) {
  expect(output.name.endsWith(`.${EXT[format]}`), output.name).toBe(true);
  const stream = videoStream(ffprobe(output.file));
  expect(stream?.codec_name, output.name).toBe(CODEC[format]);
  if (size) expect({ width: stream?.width, height: stream?.height }, output.name).toEqual(size);
}

/** shot.png / image.webp: left half opaque, right half transparent. */
function expectTransparentRight(output: Output) {
  expect(pixel(output.file, 600, 300)[3], `${output.name} right half alpha`).toBeLessThan(10);
  expect(pixel(output.file, 100, 300)[3], `${output.name} left half alpha`).toBe(255);
}

function expectWhiteRight(output: Output) {
  const [r, g, b] = pixel(output.file, 600, 300);
  expect(Math.min(r, g, b), `${output.name} transparent area is white`).toBeGreaterThan(245);
}

function expectAudio(output: Output, target: "mp3" | "wav" | "m4a") {
  expect(output.name.endsWith(`.${target}`), output.name).toBe(true);
  const probe = ffprobe(output.file);
  expect(videoStream(probe), `${output.name} has no video`).toBeUndefined();
  expect(audioStream(probe)?.codec_name, output.name).toBe(CODEC[target]);
  expect(probe.duration, `${output.name} duration`).toBeGreaterThan(2.5);
}

function expectMp4(output: Output, size?: { width: number; height: number }) {
  expect(output.name.endsWith(".mp4"), output.name).toBe(true);
  const probe = ffprobe(output.file);
  const video = videoStream(probe);
  expect(video?.codec_name, `${output.name} video`).toBe("h264");
  expect(audioStream(probe)?.codec_name, `${output.name} audio`).toBe("aac");
  if (size) expect({ width: video?.width, height: video?.height }, output.name).toEqual(size);
  expect(probe.duration, `${output.name} duration`).toBeGreaterThan(2.5);
}

/** H.264 moved into MP4 untouched: identical packets, near-identical size. */
function expectStreamCopy(output: Output, source: FixtureName) {
  expectMp4(output);
  expect(streamHash(output.file, "v:0"), `${output.name} video packets`).toBe(streamHash(fixture(source), "v:0"));
  const ratio = sizeOf(output.file) / sizeOf(fixture(source));
  expect(ratio, `${output.name} size vs ${source}`).toBeGreaterThan(0.9);
  expect(ratio, `${output.name} size vs ${source}`).toBeLessThan(1.1);
}

// ── option helpers ──────────────────────────────────────────────────────

async function pickRadio(page: Page, pill: string, name: string) {
  const pop = await openPill(page, pill);
  await pop.getByRole("radio", { name, exact: true }).click();
  await page.keyboard.press("Escape");
}

async function pickMenu(page: Page, pill: string, name: string) {
  const pop = await openPill(page, pill);
  await pop.getByRole("menuitemradio", { name, exact: true }).click();
}

// ── per tool ────────────────────────────────────────────────────────────

const SOURCE_FIXTURE: Record<string, FixtureName> = {
  heic: "iphone.heic",
  png: "shot.png",
  jpg: "photo.jpg",
  webp: "image.webp",
  avif: "image.avif",
  mov: "clip.mov",
  mp4: "clip.mp4",
  webm: "rec.webm",
  mkv: "movie.mkv",
  wav: "song.wav",
  m4a: "voice.m4a",
  flac: "track.flac",
  mp3: "song.mp3",
};
const KIND_FIXTURE: Record<Tool["category"], FixtureName> = { image: "photo.jpg", video: "clip.mp4", audio: "song.wav" };

/** A generic case from the tool's own data, for tools added without a specific case. */
export function defaultCase(tool: Tool): ToolCase {
  const source = SOURCE_FIXTURE[tool.from[0] ?? ""] ?? KIND_FIXTURE[tool.category];
  return {
    fixtures: [source],
    verify: (outputs) => {
      const output = one(outputs);
      if (tool.output === "mp4") return expectMp4(output);
      if (tool.output === "mp3" || tool.output === "wav" || tool.output === "m4a") return expectAudio(output, tool.output);
      if (tool.output === "gif") return expect(videoStream(ffprobe(output.file))?.codec_name).toBe("gif");
      if (tool.output === "jpeg" || tool.output === "png" || tool.output === "webp") return expectImage(output, tool.output);
      expect(videoStream(ffprobe(output.file))?.codec_name).toMatch(/^(mjpeg|png|webp)$/);
    },
  };
}

const targetSize = (kb: number): ToolCase => ({
  fixtures: ["large.jpg"],
  verify: (outputs) => {
    const output = one(outputs);
    expectImage(output, "jpeg");
    expect(sizeOf(output.file), `${output.name} ≤ ${kb} KB`).toBeLessThanOrEqual(kb * 1024);
    // Real effort to use the budget, not a thumbnail.
    expect(sizeOf(output.file), `${output.name} uses the budget`).toBeGreaterThan(kb * 1024 * 0.5);
    // Shrunk only as needed, never enlarged, aspect ratio kept.
    const stream = videoStream(ffprobe(output.file))!;
    expect(stream.width).toBeLessThanOrEqual(3000);
    expect(Math.abs(stream.width! / stream.height! - 4 / 3)).toBeLessThan(0.01);
  },
});

export const CASES: Record<string, ToolCase> = {
  "heic-to-jpg": { fixtures: ["iphone.heic"], verify: (o) => expectImage(one(o), "jpeg", { width: 1600, height: 1200 }) },
  "heic-to-png": { fixtures: ["iphone.heic"], verify: (o) => expectImage(one(o), "png", { width: 1600, height: 1200 }) },
  "png-to-jpg": {
    fixtures: ["shot.png"],
    verify: (o) => {
      expectImage(one(o), "jpeg", { width: 800, height: 600 });
      expectWhiteRight(one(o));
    },
  },
  "jpg-to-png": { fixtures: ["photo.jpg"], verify: (o) => expectImage(one(o), "png", { width: 2000, height: 1500 }) },
  "webp-to-jpg": {
    fixtures: ["image.webp"],
    verify: (o) => {
      expectImage(one(o), "jpeg", { width: 800, height: 600 });
      expectWhiteRight(one(o));
    },
  },
  "webp-to-png": {
    fixtures: ["image.webp"],
    verify: (o) => {
      expectImage(one(o), "png", { width: 800, height: 600 });
      expectTransparentRight(one(o));
    },
  },
  "jpg-to-webp": { fixtures: ["photo.jpg"], verify: (o) => expectImage(one(o), "webp", { width: 2000, height: 1500 }) },
  "png-to-webp": {
    fixtures: ["shot.png"],
    verify: (o) => {
      expectImage(one(o), "webp", { width: 800, height: 600 });
      expectTransparentRight(one(o));
    },
  },
  "avif-to-jpg": { fixtures: ["image.avif"], verify: (o) => expectImage(one(o), "jpeg", { width: 1200, height: 900 }) },
  "image-converter": {
    fixtures: ["photo.jpg", "shot.png", "image.webp", "iphone.heic"],
    verify: (o) => {
      expect(o).toHaveLength(4);
      expectImage(one(o, "photo-wemute.jpg"), "jpeg", { width: 2000, height: 1500 });
      expectImage(one(o, "shot.jpg"), "jpeg", { width: 800, height: 600 });
      expectWhiteRight(one(o, "shot.jpg"));
      expectImage(one(o, "image.jpg"), "jpeg", { width: 800, height: 600 });
      expectImage(one(o, "iphone.jpg"), "jpeg", { width: 1600, height: 1200 });
    },
  },
  "compress-image": {
    fixtures: ["photo.jpg", "shot.png"],
    verify: (o) => {
      expect(o).toHaveLength(2);
      const photo = one(o, "photo-wemute.jpg");
      expectImage(photo, "jpeg", { width: 2000, height: 1500 });
      expect(sizeOf(photo.file)).toBeLessThan(sizeOf(fixture("photo.jpg")));
      // A transparent PNG becomes WebP so the transparency survives.
      const shot = one(o, "shot.webp");
      expectImage(shot, "webp", { width: 800, height: 600 });
      expectTransparentRight(shot);
      expect(sizeOf(shot.file)).toBeLessThan(sizeOf(fixture("shot.png")));
    },
  },
  "compress-image-to-50kb": targetSize(50),
  "compress-image-to-100kb": targetSize(100),
  "compress-image-to-200kb": targetSize(200),
  "resize-image": {
    fixtures: ["photo.jpg", "shot.png"],
    verify: (o) => {
      expect(o).toHaveLength(2);
      expectImage(one(o, "photo-wemute.jpg"), "jpeg", { width: 1920, height: 1440 });
      // Already smaller than 1920: kept at its size, format and transparency.
      const shot = one(o, "shot-wemute.png");
      expectImage(shot, "png", { width: 800, height: 600 });
      expectTransparentRight(shot);
    },
  },
  "round-corners": {
    fixtures: ["photo.jpg"],
    verify: (o) => {
      const output = one(o);
      expectImage(output, "png", { width: 2000, height: 1500 });
      expect(pixel(output.file, 0, 0)[3], "corner is transparent").toBe(0);
      expect(pixel(output.file, 1999, 1499)[3], "corner is transparent").toBe(0);
      expect(pixel(output.file, 1000, 750)[3], "centre is opaque").toBe(255);
      expect(pixel(output.file, 1000, 0)[3], "edge midpoint is opaque").toBe(255);
    },
  },
  "mp4-to-mp3": {
    // Audio extraction pages also take audio files.
    fixtures: ["clip.mp4", "voice.m4a"],
    verify: (o) => {
      expect(o).toHaveLength(2);
      expectAudio(one(o, "clip.mp3"), "mp3");
      expectAudio(one(o, "voice.mp3"), "mp3");
    },
  },
  "mov-to-mp4": {
    fixtures: ["clip.mov", "hevc.mov"],
    verify: (o) => {
      expect(o).toHaveLength(2);
      expectStreamCopy(one(o, "clip.mp4"), "clip.mov");
      // HEVC is re-encoded to H.264 so it plays everywhere.
      const hevc = one(o, "hevc.mp4");
      expectMp4(hevc, { width: 640, height: 360 });
      expect(streamHash(hevc.file, "v:0")).not.toBe(streamHash(fixture("hevc.mov"), "v:0"));
    },
  },
  "mkv-to-mp4": { fixtures: ["movie.mkv"], verify: (o) => expectStreamCopy(one(o), "movie.mkv") },
  "webm-to-mp4": { fixtures: ["rec.webm"], verify: (o) => expectMp4(one(o), { width: 640, height: 360 }) },
  "video-to-gif": {
    fixtures: ["clip.mp4"],
    configure: async (page) => {
      // Width 320 (More options…), start at 1 s, length 1.5 s.
      const pop = await openPill(page, "pill-video-format");
      await pop.getByRole("menuitem").click();
      await pop.getByRole("radio", { name: "320", exact: true }).click();
      await page.keyboard.press("Escape");
      await pickRadio(page, "pill-gif-start", "1");
      const length = await openPill(page, "pill-gif-length");
      await length.getByRole("spinbutton").fill("1.5");
      await page.keyboard.press("Escape");
      await expect(page.getByTestId("pill-gif-length")).toContainText("1.5");
      await expect(page.getByTestId("pill-gif-start")).toContainText("1");
    },
    verify: (o) => {
      const output = one(o);
      expect(output.name).toBe("clip.gif");
      const probe = ffprobe(output.file);
      const stream = videoStream(probe)!;
      expect(stream.codec_name).toBe("gif");
      expect(stream.width).toBe(320);
      expect(stream.height).toBe(180);
      expect(probe.duration).toBeGreaterThan(1.3);
      expect(probe.duration).toBeLessThan(1.7);
    },
  },
  "compress-video": {
    fixtures: ["clip.mp4"],
    configure: async (page) => {
      await pickMenu(page, "pill-video-size", "480p");
      await expect(page.getByTestId("pill-video-size")).toContainText("480p");
    },
    verify: (o) => {
      const output = one(o);
      expect(output.name).toBe("clip-small.mp4");
      expectMp4(output);
      const stream = videoStream(ffprobe(output.file))!;
      expect(stream.height).toBeLessThanOrEqual(480);
      expect(Math.abs(stream.width! - (stream.height! * 16) / 9)).toBeLessThan(3);
      expect(sizeOf(output.file)).toBeLessThan(sizeOf(fixture("clip.mp4")));
    },
  },
  "wav-to-mp3": { fixtures: ["song.wav"], verify: (o) => expectAudio(one(o), "mp3") },
  "m4a-to-mp3": { fixtures: ["voice.m4a"], verify: (o) => expectAudio(one(o), "mp3") },
  "flac-to-mp3": { fixtures: ["track.flac"], verify: (o) => expectAudio(one(o), "mp3") },
  "mp3-to-wav": { fixtures: ["song.mp3"], verify: (o) => expectAudio(one(o), "wav") },
};

export function caseFor(tool: Tool): { toolCase: ToolCase; generic: boolean } {
  const specific = CASES[tool.slug];
  return specific ? { toolCase: specific, generic: false } : { toolCase: defaultCase(tool), generic: true };
}
