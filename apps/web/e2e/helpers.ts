import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test as base, type Locator, type Page, type TestInfo } from "@playwright/test";
import { unzipSync } from "fflate";
import { FFMPEG_CORE_BASE } from "../src/lib/media";
import { ENGINE_DIR, FIXTURE_DIR } from "./paths";

// ── fixtures on disk ────────────────────────────────────────────────────

export type FixtureName =
  | "photo.jpg"
  | "shot.png"
  | "image.webp"
  | "image.avif"
  | "iphone.heic"
  | "large.jpg"
  | "clip.mov"
  | "clip.mp4"
  | "rec.webm"
  | "movie.mkv"
  | "hevc.mov"
  | "song.wav"
  | "voice.m4a"
  | "track.flac"
  | "song.mp3"
  | "tiny.jpg"
  | "movie-opus.mkv"
  | "silent.mp4"
  | "notes.txt"
  | "broken.png"
  | "broken.heic";

export function fixture(name: FixtureName): string {
  return path.join(FIXTURE_DIR, name);
}

/** Why make.sh could not produce a fixture, or undefined when it exists. */
export function missingFixture(name: FixtureName): string | undefined {
  if (existsSync(fixture(name))) return undefined;
  const skipped = existsSync(path.join(FIXTURE_DIR, "skipped.txt")) ? readFileSync(path.join(FIXTURE_DIR, "skipped.txt"), "utf8") : "";
  const line = skipped.split("\n").find((entry) => entry.startsWith(`${name}:`));
  return line ? line.slice(name.length + 1).trim() : `${name} was not generated`;
}

// ── probing outputs ─────────────────────────────────────────────────────

export interface ProbeStream {
  codec_name: string;
  codec_type: string;
  width?: number;
  height?: number;
  pix_fmt?: string;
}

export interface ProbeResult {
  streams: ProbeStream[];
  duration: number;
}

export function ffprobe(file: string): ProbeResult {
  const json = execFileSync(
    "ffprobe",
    ["-v", "error", "-show_entries", "stream=codec_name,codec_type,width,height,pix_fmt:format=duration", "-of", "json", file],
    { encoding: "utf8" },
  );
  const data = JSON.parse(json) as { streams: ProbeStream[]; format?: { duration?: string } };
  return { streams: data.streams, duration: Number(data.format?.duration ?? 0) };
}

export const videoStream = (probe: ProbeResult) => probe.streams.find((stream) => stream.codec_type === "video");
export const audioStream = (probe: ProbeResult) => probe.streams.find((stream) => stream.codec_type === "audio");

/** RGBA of one pixel, decoded by FFmpeg. */
export function pixel(file: string, x: number, y: number): [number, number, number, number] {
  const raw = execFileSync("ffmpeg", ["-v", "error", "-i", file, "-vf", `format=rgba,crop=1:1:${x}:${y}`, "-frames:v", "1", "-f", "rawvideo", "-"]);
  return [raw[0], raw[1], raw[2], raw[3]];
}

/** MD5 of the encoded packets of one stream, to prove a stream copy. */
export function streamHash(file: string, stream: "v:0" | "a:0"): string {
  return execFileSync("ffmpeg", ["-v", "error", "-i", file, "-map", `0:${stream}`, "-c", "copy", "-f", "md5", "-"], { encoding: "utf8" }).trim();
}

export function sizeOf(file: string): number {
  return readFileSync(file).byteLength;
}

// ── page helpers ────────────────────────────────────────────────────────

export function converter(page: Page): Locator {
  return page.getByTestId("converter");
}

/** Navigate and wait until the React island has hydrated. */
export async function openConverter(page: Page, url: string): Promise<void> {
  await page.goto(url);
  await page.locator("astro-island:not([ssr]) [data-testid=converter]").waitFor();
}

export async function addFiles(page: Page, names: FixtureName[]): Promise<void> {
  await page.getByTestId("file-input").setInputFiles(names.map(fixture));
}

export async function waitForPhase(page: Page, phase: "empty" | "ready" | "running" | "done", timeout = 150_000): Promise<void> {
  await expect(converter(page)).toHaveAttribute("data-phase", phase, { timeout });
}

/** Open a pill and return its popover. */
export async function openPill(page: Page, testId: string): Promise<Locator> {
  const pill = page.getByTestId(testId);
  await pill.click();
  await expect(pill).toHaveAttribute("aria-expanded", "true");
  return pill.locator("xpath=..").locator(".cv-pop");
}

export interface Output {
  name: string;
  file: string;
}

/**
 * Press "Download"/"Download all" and save what the browser downloads. A ZIP is
 * unpacked so every entry can be checked like a single download.
 */
export async function downloadResults(page: Page, testInfo: TestInfo): Promise<{ zip: boolean; name: string; outputs: Output[] }> {
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("download-all").click()]);
  const name = download.suggestedFilename();
  const saved = testInfo.outputPath(name);
  await download.saveAs(saved);
  if (!name.endsWith(".zip")) return { zip: false, name, outputs: [{ name, file: saved }] };
  const entries = unzipSync(readFileSync(saved));
  const outputs = Object.entries(entries).map(([entry, data]) => {
    const file = testInfo.outputPath(`unzipped-${entry}`);
    writeFileSync(file, data);
    return { name: entry, file };
  });
  return { zip: true, name, outputs };
}

// ── test with page health checks ────────────────────────────────────────

const ENGINE_VERSION = /@ffmpeg\/core@([^/]+)/.exec(FFMPEG_CORE_BASE)![1];

export const test = base.extend<{ consoleErrors: string[] }>({
  consoleErrors: [
    async ({ page }, use, testInfo) => {
      const errors: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(`console.error: ${message.text()}`);
      });
      page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
      // Serve the pinned FFmpeg core from a local copy (set E2E_LIVE_CDN=1 to use jsDelivr).
      if (!process.env.E2E_LIVE_CDN) {
        await page.route(`${FFMPEG_CORE_BASE}/*`, async (route) => {
          const name = new URL(route.request().url()).pathname.split("/").pop()!;
          const file = path.join(ENGINE_DIR, `${ENGINE_VERSION}-${name}`);
          if (!existsSync(file)) return route.continue();
          await route.fulfill({
            body: readFileSync(file),
            headers: {
              "content-type": name.endsWith(".wasm") ? "application/wasm" : "text/javascript",
              "access-control-allow-origin": "*",
            },
          });
        });
      }
      // Unhandled promise rejections surface as pageerror in Chromium; also count them explicitly.
      await page.addInitScript(() => {
        window.addEventListener("unhandledrejection", (event) => {
          console.error(`unhandledrejection: ${String((event as PromiseRejectionEvent).reason)}`);
        });
      });
      await use(errors);
      const allowed = (testInfo.annotations.find((note) => note.type === "allowed-console")?.description ?? "").split("|").filter(Boolean);
      const unexpected = errors.filter((error) => !allowed.some((pattern) => error.includes(pattern)));
      expect(unexpected, "console errors / unhandled rejections").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
