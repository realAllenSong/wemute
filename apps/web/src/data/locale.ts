export type Locale = "en" | "zh";

export const LOCALES: Locale[] = ["en", "zh"];

export const HTML_LANG: Record<Locale, string> = { en: "en", zh: "zh-CN" };
export const OG_LOCALE: Record<Locale, string> = { en: "en_US", zh: "zh_CN" };

export type Text = Record<Locale, string>;

export function text(en: string, zh: string): Text {
  return { en, zh };
}

/** Path for a slug in a locale: "" is the home page. */
export function localePath(locale: Locale, slug = ""): string {
  const tail = slug ? `/${slug}` : "";
  if (locale === "en") return tail || "/";
  return `/zh${tail}`;
}

/** The slug of a pathname without its locale prefix. */
export function slugFromPath(pathname: string): string {
  return pathname.replace(/^\/zh(?=\/|$)/, "").replace(/^\/+|\/+$/g, "");
}

export function localeFromPath(pathname: string): Locale {
  return /^\/zh(\/|$)/.test(pathname) ? "zh" : "en";
}
