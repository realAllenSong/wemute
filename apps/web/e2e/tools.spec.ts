import { TOOLS, type Tool } from "../src/data/tools";
import { caseFor } from "./cases";
import { addFiles, downloadResults, expect, missingFixture, openConverter, test, waitForPhase } from "./helpers";

// Chinese pages share the engine with English ones; a sample across every mode is enough.
const ZH_SAMPLE = new Set(["heic-to-jpg", "png-to-webp", "compress-image-to-100kb", "resize-image", "mov-to-mp4", "video-to-gif", "flac-to-mp3"]);

const autoStarts = (tool: Tool) => tool.category !== "video";

for (const tool of TOOLS) {
  for (const locale of ["en", "zh"] as const) {
    if (locale === "zh" && !ZH_SAMPLE.has(tool.slug)) continue;
    const url = locale === "en" ? `/${tool.slug}` : `/zh/${tool.slug}`;

    test(`${url} converts and downloads a verified file`, async ({ page }, testInfo) => {
      const { toolCase, generic } = caseFor(tool);
      if (generic) testInfo.annotations.push({ type: "generic-case", description: `no specific case for ${tool.slug}; checked by output type` });
      for (const name of toolCase.fixtures) {
        const reason = missingFixture(name);
        test.skip(Boolean(reason), `${name}: ${reason}`);
      }

      await openConverter(page, url);
      await toolCase.before?.(page);
      await addFiles(page, toolCase.fixtures);
      await expect(page.getByTestId("file-card")).toHaveCount(toolCase.fixtures.length);

      // Image and audio pages start on their own; video pages wait for Convert.
      if (!autoStarts(tool)) {
        await waitForPhase(page, "ready");
        await expect(page.getByTestId("file-card").and(page.locator("[data-status=reading]"))).toHaveCount(0);
        await toolCase.configure?.(page);
        await page.getByTestId("convert").click();
      }

      await waitForPhase(page, "done");
      await expect(page.locator("[data-testid=file-card][data-status=error]")).toHaveCount(0);
      await expect(page.locator("[data-testid=file-card][data-status=done]")).toHaveCount(toolCase.fixtures.length);

      const { zip, outputs } = await downloadResults(page, testInfo);
      expect(zip, "several results download as one ZIP").toBe(toolCase.fixtures.length > 1);
      toolCase.verify(outputs);
    });
  }
}
