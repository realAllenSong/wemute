import type { Page, Route } from "@playwright/test";
import { FFMPEG_CORE_BASE } from "../src/lib/media";
import { expectImage } from "./cases";
import { addFiles, audioStream, downloadResults, expect, ffprobe, fixture, openConverter, openPill, sizeOf, streamHash, test, videoStream, waitForPhase } from "./helpers";

const cardsWith = (page: Page, status: string) => page.locator(`[data-testid=file-card][data-status=${status}]`);

/** Hold the FFmpeg core download until `release()` is called. */
async function holdEngine(page: Page) {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route(`${FFMPEG_CORE_BASE}/*`, async (route: Route) => {
    await gate;
    await route.fallback();
  });
  return release;
}

test("a corrupt HEIC says it couldn't be decoded", async ({ page }) => {
  await openConverter(page, "/heic-to-jpg");
  await addFiles(page, ["broken.heic"]);
  await expect(cardsWith(page, "error")).toHaveAttribute("title", /broken\.heic — This HEIC file couldn't be decoded/);
  await expect(page.getByTestId("retry-failed")).toBeVisible();
});

test("compressing never hands back a bigger file", async ({ page }, testInfo) => {
  await openConverter(page, "/compress-image");
  await addFiles(page, ["tiny.jpg"]);
  await waitForPhase(page, "done");
  const { outputs } = await downloadResults(page, testInfo);
  expectImage(outputs[0], "jpeg", { width: 2000, height: 1500 });
  expect(sizeOf(outputs[0].file)).toBeLessThanOrEqual(sizeOf(fixture("tiny.jpg")));
});

test("MKV with H.264 and Opus keeps the video and converts only the audio", async ({ page }, testInfo) => {
  await openConverter(page, "/mkv-to-mp4");
  await addFiles(page, ["movie-opus.mkv"]);
  await waitForPhase(page, "ready");
  await page.getByTestId("convert").click();
  await waitForPhase(page, "done");
  const { outputs } = await downloadResults(page, testInfo);
  const probe = ffprobe(outputs[0].file);
  expect(videoStream(probe)?.codec_name).toBe("h264");
  expect(audioStream(probe)?.codec_name).toBe("aac");
  expect(streamHash(outputs[0].file, "v:0")).toBe(streamHash(fixture("movie-opus.mkv"), "v:0"));
});

test("a video without sound explains there is no audio to extract", async ({ page }) => {
  await openConverter(page, "/mp4-to-mp3");
  await addFiles(page, ["silent.mp4"]);
  await waitForPhase(page, "ready");
  await page.getByTestId("convert").click();
  await waitForPhase(page, "done");
  await expect(cardsWith(page, "error")).toHaveAttribute("title", /silent\.mp4 — This file has no audio track to convert/);
});

test("Stop while the engine is loading cancels, and Convert runs again", async ({ page }, testInfo) => {
  await openConverter(page, "/mov-to-mp4");
  const release = await holdEngine(page);
  await addFiles(page, ["clip.mov"]);
  await waitForPhase(page, "ready");
  await page.getByTestId("convert").click();
  await expect(page.getByText(/Loading converter engine/)).toBeVisible();
  await page.getByTestId("stop").click();
  release();
  await waitForPhase(page, "ready");
  await expect(cardsWith(page, "cancelled")).toHaveCount(1);
  // Give a wrongly continuing job time to finish; it must stay cancelled.
  await page.waitForTimeout(2_000);
  await expect(cardsWith(page, "cancelled")).toHaveCount(1);

  await page.getByTestId("convert").click();
  await waitForPhase(page, "done");
  const { outputs } = await downloadResults(page, testInfo);
  expect(outputs.map((output) => output.name)).toEqual(["clip.mp4"]);
});

test("Stop during an encode cancels it, and Convert runs again", async ({ page }, testInfo) => {
  await openConverter(page, "/compress-video");
  await addFiles(page, ["clip.mp4"]);
  await waitForPhase(page, "ready");
  await page.getByTestId("convert").click();
  await expect(page.getByText(/Loading converter engine/)).toHaveCount(0);
  await expect(page.locator(".cv-meter")).toBeVisible();
  await page.getByTestId("stop").click();
  await waitForPhase(page, "ready");
  await expect(cardsWith(page, "cancelled")).toHaveCount(1);

  await page.getByTestId("convert").click();
  await waitForPhase(page, "done");
  const { outputs } = await downloadResults(page, testInfo);
  expect(videoStream(ffprobe(outputs[0].file))?.height).toBeLessThanOrEqual(720);
});

test("a GIF start past the end of the clip fails honestly instead of saving an empty GIF", async ({ page }) => {
  await openConverter(page, "/video-to-gif");
  await addFiles(page, ["clip.mp4"]);
  await waitForPhase(page, "ready");
  const pop = await openPill(page, "pill-gif-start");
  await pop.getByRole("radio", { name: "10", exact: true }).click();
  await page.keyboard.press("Escape");
  await page.getByTestId("convert").click();
  await waitForPhase(page, "done");
  await expect(cardsWith(page, "done")).toHaveCount(0);
  await expect(cardsWith(page, "error")).toHaveAttribute("title", /clip\.mp4 — The start time is past the end of this video/);
});

test("files added while a batch runs are converted too", async ({ page }, testInfo) => {
  await openConverter(page, "/wav-to-mp3");
  const release = await holdEngine(page);
  await addFiles(page, ["song.wav"]);
  await waitForPhase(page, "running");
  await addFiles(page, ["track.flac"]);
  release();
  await expect(cardsWith(page, "done")).toHaveCount(2, { timeout: 60_000 });
  await waitForPhase(page, "done");
  const { zip, outputs } = await downloadResults(page, testInfo);
  expect(zip).toBe(true);
  expect(outputs.map((output) => output.name).sort()).toEqual(["song.mp3", "track.mp3"]);
});

test("Enter starts a ready batch", async ({ page }) => {
  await openConverter(page, "/");
  await addFiles(page, ["photo.jpg"]);
  await waitForPhase(page, "ready");
  await page.locator("body").click({ position: { x: 5, y: 5 } });
  await page.keyboard.press("Enter");
  await waitForPhase(page, "done");
});
