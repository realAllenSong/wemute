import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";
import { TOOLS } from "../src/data/tools";
import { FFMPEG_CORE_BASE } from "../src/lib/media";
import { expectImage } from "./cases";
import {
  addFiles,
  audioStream,
  converter,
  downloadResults,
  expect,
  ffprobe,
  fixture,
  openConverter,
  openPill,
  test,
  videoStream,
  waitForPhase,
  type FixtureName,
} from "./helpers";
import { E2E_DIR } from "./paths";

const cards = (page: Page) => page.getByTestId("file-card");
const cardsWith = (page: Page, status: string) => page.locator(`[data-testid=file-card][data-status=${status}]`);

const MIME: Partial<Record<FixtureName, string>> = {
  "photo.jpg": "image/jpeg",
  "shot.png": "image/png",
  "song.wav": "audio/wav",
  "clip.mov": "video/quicktime",
};

/** Every page in the build, so new pages are checked without listing them. */
function builtPages(): string[] {
  const client = path.join(E2E_DIR, "..", "dist", "client");
  const walk = (dir: string, prefix: string): string[] =>
    readdirSync(dir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("_"))
      .flatMap((entry) => {
        const url = `${prefix}/${entry.name}`;
        const own = existsSync(path.join(dir, entry.name, "index.html")) ? [url] : [];
        return [...own, ...walk(path.join(dir, entry.name), url)];
      });
  if (!existsSync(client)) throw new Error("Build the site first: npm run build");
  return ["/", ...walk(client, "")];
}

function payload(name: FixtureName) {
  return { name, type: MIME[name] ?? "", base64: readFileSync(fixture(name)).toString("base64") };
}

test.describe("home converter", () => {
  test("mixed batch: one sentence per kind, Convert, ZIP with every result", async ({ page }, testInfo) => {
    await openConverter(page, "/");
    await addFiles(page, ["photo.jpg", "clip.mov", "song.wav"]);
    await waitForPhase(page, "ready");

    const lines = page.getByTestId("sentence-line");
    await expect(lines).toHaveCount(3);
    await expect(lines.nth(0)).toHaveAttribute("data-kind", "image");
    await expect(lines.nth(0)).toHaveText(/Convert 1 image to JPG/);
    await expect(lines.nth(1)).toHaveText(/Convert 1 video to MP4/);
    await expect(lines.nth(2)).toHaveText(/Convert 1 audio file to MP3/);

    // The home page waits for Convert even for images.
    await expect(cardsWith(page, "ready")).toHaveCount(3);
    await page.getByTestId("convert").click();
    await waitForPhase(page, "done");
    await expect(page.getByTestId("done")).toContainText("3 files are ready");

    const { zip, name, outputs } = await downloadResults(page, testInfo);
    expect(zip).toBe(true);
    expect(name).toBe("wemute-files.zip");
    expect(outputs.map((output) => output.name).sort()).toEqual(["clip.mp4", "photo-wemute.jpg", "song.mp3"]);
    expectImage(outputs.find((output) => output.name === "photo-wemute.jpg")!, "jpeg", { width: 2000, height: 1500 });
    expect(videoStream(ffprobe(outputs.find((output) => output.name === "clip.mp4")!.file))?.codec_name).toBe("h264");
    expect(audioStream(ffprobe(outputs.find((output) => output.name === "song.mp3")!.file))?.codec_name).toBe("mp3");
  });

  test("a per-file download saves just that file", async ({ page }, testInfo) => {
    await openConverter(page, "/");
    await addFiles(page, ["photo.jpg", "shot.png"]);
    await page.getByTestId("convert").click();
    await waitForPhase(page, "done");
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("card-download").nth(1).click()]);
    expect(download.suggestedFilename()).toBe("shot.jpg");
    const saved = testInfo.outputPath("shot.jpg");
    await download.saveAs(saved);
    expectImage({ name: "shot.jpg", file: saved }, "jpeg", { width: 800, height: 600 });
  });

  test("unsupported files are skipped with a visible notice", async ({ page }) => {
    await openConverter(page, "/");
    await addFiles(page, ["notes.txt", "photo.jpg"]);
    await expect(page.getByTestId("notice")).toContainText("notes.txt");
    await expect(cards(page)).toHaveCount(1);
    await expect(cards(page).first()).toHaveAttribute("data-kind", "image");
  });

  test("a tool page skips files of another kind and stays empty", async ({ page }) => {
    await openConverter(page, "/heic-to-jpg");
    await addFiles(page, ["song.wav"]);
    await expect(page.getByTestId("notice")).toContainText("song.wav");
    await expect(converter(page)).toHaveAttribute("data-phase", "empty");
  });

  test("a corrupt file fails on its own and retry leaves finished files alone", async ({ page }, testInfo) => {
    await openConverter(page, "/");
    await addFiles(page, ["broken.png", "photo.jpg"]);
    await expect(cardsWith(page, "error")).toHaveCount(1);
    await expect(cardsWith(page, "ready")).toHaveCount(1);
    await page.getByTestId("convert").click();
    await waitForPhase(page, "done");
    await expect(page.getByTestId("done")).toContainText("1 done, 1 failed");
    await expect(cardsWith(page, "error")).toHaveAttribute("title", /broken\.png — Your browser can't read this image/);

    await page.getByTestId("retry-failed").click();
    await waitForPhase(page, "done");
    await expect(cardsWith(page, "done")).toHaveCount(1);
    await expect(cardsWith(page, "error")).toHaveCount(1);
    await expect(page.getByTestId("retry-failed")).toContainText("Retry 1 failed");

    const { zip, outputs } = await downloadResults(page, testInfo);
    expect(zip).toBe(false);
    expectImage(outputs[0], "jpeg", { width: 2000, height: 1500 });
  });

  test("retry recovers a file that failed for a temporary reason", async ({ page }, testInfo) => {
    testInfo.annotations.push({ type: "allowed-console", description: "converter engine failed to load|Failed to load resource|net::ERR_FAILED" });
    const offline = (route: import("@playwright/test").Route) => route.abort();
    await page.route(`${FFMPEG_CORE_BASE}/*`, offline);
    await openConverter(page, "/");
    await addFiles(page, ["photo.jpg", "clip.mov"]);
    await page.getByTestId("convert").click();
    await waitForPhase(page, "done");
    await expect(cardsWith(page, "error")).toHaveAttribute("title", /clip\.mov — The converter engine couldn't load/);
    await expect(cardsWith(page, "done")).toHaveCount(1);

    await page.unroute(`${FFMPEG_CORE_BASE}/*`, offline);
    await page.getByTestId("retry-failed").click();
    await waitForPhase(page, "done");
    await expect(cardsWith(page, "done")).toHaveCount(2);
    await expect(page.getByTestId("retry-failed")).toHaveCount(0);
    const { outputs } = await downloadResults(page, testInfo);
    expect(outputs.map((output) => output.name).sort()).toEqual(["clip.mp4", "photo-wemute.jpg"]);
  });

  test("“Convert another batch” resets to the empty picker", async ({ page }) => {
    await openConverter(page, "/");
    await addFiles(page, ["photo.jpg"]);
    await page.getByTestId("convert").click();
    await waitForPhase(page, "done");
    await page.getByTestId("convert-more").click();
    await waitForPhase(page, "empty");
    await expect(cards(page)).toHaveCount(0);
    await expect(page.getByTestId("pill-source")).toBeVisible();
    // And it works again from scratch.
    await addFiles(page, ["shot.png"]);
    await expect(page.getByTestId("sentence-line")).toHaveText(/Convert 1 image to JPG/);
  });

  test("removing a file updates the sentence", async ({ page }) => {
    await openConverter(page, "/");
    await addFiles(page, ["photo.jpg", "shot.png", "song.wav"]);
    await expect(page.getByTestId("sentence-line").first()).toHaveText(/Convert 2 images/);
    await page.getByRole("button", { name: "Remove shot.png" }).click();
    await expect(page.getByTestId("sentence-line").first()).toHaveText(/Convert 1 image/);
    await page.getByRole("button", { name: "Remove song.wav" }).click();
    await expect(page.getByTestId("sentence-line")).toHaveCount(1);
  });
});

test.describe("picker", () => {
  test("source pill on home navigates to the matching tool, “any file” returns home", async ({ page }) => {
    await openConverter(page, "/");
    const pop = await openPill(page, "pill-source");
    await pop.getByRole("menuitemradio", { name: "MOV videos" }).click();
    await page.waitForURL("**/mov-to-mp4");
    await page.locator("astro-island:not([ssr]) [data-testid=converter]").waitFor();
    await expect(page.getByTestId("pill-source")).toContainText("MOV videos");

    const back = await openPill(page, "pill-source");
    await back.getByRole("menuitemradio", { name: "any file" }).click();
    await page.waitForURL((url) => url.pathname === "/");
  });

  test("target pill on home opens the chosen conversion", async ({ page }) => {
    await openConverter(page, "/");
    await expect(page.getByTestId("pill-source")).toContainText("HEIC photos");
    const pop = await openPill(page, "pill-target");
    await pop.getByRole("menuitemradio", { name: "PNG" }).click();
    await page.waitForURL("**/heic-to-png");
  });

  test("switching source on a tool page keeps the target when it exists", async ({ page }) => {
    await openConverter(page, "/heic-to-jpg");
    const pop = await openPill(page, "pill-source");
    await pop.getByRole("menuitemradio", { name: "PNG images" }).click();
    await page.waitForURL("**/png-to-jpg");
  });

  test("Chinese picker stays in /zh", async ({ page }) => {
    await openConverter(page, "/zh");
    const pop = await openPill(page, "pill-source");
    await pop.getByRole("menuitemradio", { name: "MOV 视频" }).click();
    await page.waitForURL("**/zh/mov-to-mp4");
    await page.locator("astro-island:not([ssr]) [data-testid=converter]").waitFor();
    const back = await openPill(page, "pill-source");
    await back.getByRole("menuitemradio", { name: "任意文件" }).click();
    await page.waitForURL((url) => url.pathname === "/zh");
  });
});

test.describe("other ways to add files", () => {
  test("pasting files adds them", async ({ page }) => {
    await openConverter(page, "/");
    await page.evaluate((files) => {
      const data = new DataTransfer();
      for (const file of files) data.items.add(new File([Uint8Array.from(atob(file.base64), (c) => c.charCodeAt(0))], file.name, { type: file.type }));
      document.body.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }));
    }, [payload("photo.jpg")]);
    await expect(cards(page)).toHaveCount(1);
    await waitForPhase(page, "ready");
  });

  test("dropping files anywhere on a tool page converts them", async ({ page }, testInfo) => {
    await openConverter(page, "/png-to-jpg");
    await page.evaluate((files) => {
      const data = new DataTransfer();
      for (const file of files) data.items.add(new File([Uint8Array.from(atob(file.base64), (c) => c.charCodeAt(0))], file.name, { type: file.type }));
      const target = document.querySelector("footer") ?? document.body;
      target.dispatchEvent(new DragEvent("dragenter", { dataTransfer: data, bubbles: true, cancelable: true }));
      target.dispatchEvent(new DragEvent("dragover", { dataTransfer: data, bubbles: true, cancelable: true }));
      target.dispatchEvent(new DragEvent("drop", { dataTransfer: data, bubbles: true, cancelable: true }));
    }, [payload("shot.png")]);
    await waitForPhase(page, "done");
    const { outputs } = await downloadResults(page, testInfo);
    expectImage(outputs[0], "jpeg", { width: 800, height: 600 });
  });

  test("dropping a folder adds every visible file inside it", async ({ page }) => {
    await openConverter(page, "/");
    await page.evaluate((files) => {
      const make = (file: { name: string; type: string; base64: string }) =>
        new File([Uint8Array.from(atob(file.base64), (c) => c.charCodeAt(0))], file.name, { type: file.type });
      const fileEntry = (file: File) => ({ name: file.name, isFile: true, isDirectory: false, file: (ok: (value: File) => void) => ok(file) });
      const dirEntry = (name: string, children: unknown[]) => ({
        name,
        isFile: false,
        isDirectory: true,
        createReader: () => {
          let read = false;
          return {
            readEntries: (ok: (batch: unknown[]) => void) => {
              const batch = read ? [] : children;
              read = true;
              setTimeout(() => ok(batch));
            },
          };
        },
      });
      const [photo, song, clip] = files.map(make);
      const folder = dirEntry("Holiday", [
        fileEntry(photo),
        fileEntry(new File(["x"], ".DS_Store")),
        dirEntry("audio", [fileEntry(song)]),
        dirEntry("video", [fileEntry(clip)]),
      ]);
      // A real folder drag can't be scripted; give the dropped item a directory entry instead.
      const data = new DataTransfer();
      data.items.add(new File([], "Holiday"));
      DataTransferItem.prototype.webkitGetAsEntry = function () {
        return folder as unknown as FileSystemEntry;
      };
      document.body.dispatchEvent(new DragEvent("drop", { dataTransfer: data, bubbles: true, cancelable: true }));
    }, [payload("photo.jpg"), payload("song.wav"), payload("clip.mov")]);
    await expect(cards(page)).toHaveCount(3);
    await expect(page.getByTestId("sentence-line")).toHaveCount(3);
  });
});

test.describe("resize options", () => {
  test("50% halves, a custom width larger than the image never upscales", async ({ page }, testInfo) => {
    await openConverter(page, "/resize-image");
    const pop = await openPill(page, "pill-empty-resize");
    await pop.getByRole("radio", { name: "50%" }).click();
    await page.keyboard.press("Escape");
    await addFiles(page, ["photo.jpg"]);
    await waitForPhase(page, "done");
    let { outputs } = await downloadResults(page, testInfo);
    expectImage(outputs[0], "jpeg", { width: 1000, height: 750 });

    await page.getByTestId("convert-more").click();
    const custom = await openPill(page, "pill-empty-resize");
    await custom.getByRole("radio", { name: "Custom width" }).click();
    await custom.getByRole("spinbutton").fill("4000");
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("pill-empty-resize")).toContainText("4000 px");
    await addFiles(page, ["shot.png"]);
    await waitForPhase(page, "done");
    ({ outputs } = await downloadResults(page, testInfo));
    expectImage(outputs[0], "png", { width: 800, height: 600 });
  });
});

test.describe("page health", () => {
  test("dark mode loads cleanly", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    for (const url of ["/", "/heic-to-jpg", "/zh/compress-video"]) {
      await openConverter(page, url);
      const dark = await page.evaluate(() => {
        const [r, g, b] = getComputedStyle(document.body).backgroundColor.match(/\d+/g)!.map(Number);
        return { matches: matchMedia("(prefers-color-scheme: dark)").matches, luminance: (r + g + b) / 3 };
      });
      expect(dark.matches).toBe(true);
      expect(dark.luminance, `${url} background is dark`).toBeLessThan(80);
    }
  });

  const TOOL_PAGES = new Set(["/", "/zh", ...TOOLS.flatMap((tool) => [`/${tool.slug}`, `/zh/${tool.slug}`])]);
  for (const url of builtPages()) {
    test(`${url} loads without console errors or failed requests`, async ({ page }) => {
      const failed: string[] = [];
      page.on("response", (response) => {
        if (response.status() >= 400 && new URL(response.url()).origin === new URL(page.url() || "http://127.0.0.1:4402").origin) failed.push(`${response.status()} ${response.url()}`);
      });
      page.on("requestfailed", (request) => failed.push(`failed ${request.url()} ${request.failure()?.errorText}`));
      if (!TOOL_PAGES.has(url)) {
        const response = await page.goto(url);
        expect(response?.status()).toBe(200);
        await page.waitForLoadState("networkidle");
        expect(failed).toEqual([]);
        return;
      }
      await openConverter(page, url);
      await page.waitForLoadState("networkidle");
      // Opening and closing the source picker exercises the sentence menus.
      await openPill(page, "pill-source");
      await page.keyboard.press("Escape");
      await expect(page.getByTestId("pill-source")).toHaveAttribute("aria-expanded", "false");
      expect(failed).toEqual([]);
    });
  }
});
