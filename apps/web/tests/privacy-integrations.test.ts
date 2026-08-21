// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { analyticsConfigured, analyticsConsent, track } from "../src/lib/analytics";

describe("optional third-party integrations", () => {
  it("keeps analytics off without a configured measurement ID", () => {
    expect(analyticsConfigured).toBe(false);
    expect(analyticsConsent()).toBe("denied");
    expect(document.querySelector('script[data-wemute-analytics]')).toBeNull();
  });

  it("emits a local testable event without sending a network tag", () => {
    let detail: unknown;
    window.addEventListener("wemute:analytics", (event) => {
      detail = (event as CustomEvent).detail;
    }, { once: true });

    track("files_added", { file_count: 3, file_category: "image" });

    expect(detail).toEqual({
      event: "files_added",
      properties: { file_count: 3, file_category: "image" },
    });
    expect(document.querySelector('script[data-wemute-analytics]')).toBeNull();
  });
});
