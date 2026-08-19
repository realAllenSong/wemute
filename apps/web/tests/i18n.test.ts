import { describe, expect, it } from "vitest";
import { defaultLocale, t } from "../src/i18n";

describe("localization", () => {
  it("follows Chinese system locales", () => {
    expect(defaultLocale("zh-CN")).toBe("zh");
    expect(defaultLocale("en-US")).toBe("en");
  });

  it("has localized core actions", () => {
    expect(t("zh", "convertAll")).toBe("全部转换");
    expect(t("en", "convertAll")).toBe("Convert All");
  });
});
