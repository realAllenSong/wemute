import { HTML_LANG, localePath, type Locale } from "../data/locale";
import type { Tool } from "../data/tools";

const configured = process.env.WEMUTE_SITE_URL?.trim();

/** Only a build with an explicit public origin may be indexed. */
export const INDEXABLE = Boolean(configured) && !/localhost|127\.0\.0\.1/.test(configured ?? "");

export const ADS = (() => {
  const client = process.env.PUBLIC_ADSENSE_CLIENT?.trim() ?? "";
  const enabled = process.env.PUBLIC_ADSENSE_ENABLED === "true" && /^ca-pub-\d{10,}$/.test(client);
  return {
    enabled,
    client,
    slots: {
      content: process.env.PUBLIC_ADSENSE_SLOT_CONTENT?.trim() ?? "",
      footer: process.env.PUBLIC_ADSENSE_SLOT_FOOTER?.trim() ?? "",
    },
  };
})();

export const GA_ID = (() => {
  const value = process.env.PUBLIC_GA_MEASUREMENT_ID?.trim() ?? "";
  return /^G-[A-Z0-9]+$/.test(value) ? value : "";
})();

/** Vercel Web Analytics is cookieless, so it needs no consent prompt. */
export const VERCEL_ANALYTICS = process.env.PUBLIC_VERCEL_ANALYTICS === "true";

export function absolute(site: URL, path: string): string {
  return new URL(path, site).toString();
}

export function alternates(site: URL, slug: string) {
  return [
    { hreflang: HTML_LANG.en, href: absolute(site, localePath("en", slug)) },
    { hreflang: HTML_LANG.zh, href: absolute(site, localePath("zh", slug)) },
    { hreflang: "x-default", href: absolute(site, localePath("en", slug)) },
  ];
}

const ORGANIZATION_ID = "#organization";

export function organization(site: URL) {
  return {
    "@type": "Organization",
    "@id": absolute(site, "/") + ORGANIZATION_ID,
    name: "Wemute",
    url: absolute(site, "/"),
    logo: absolute(site, "/icon-512.png"),
  };
}

export function website(site: URL, locale: Locale, description: string) {
  return {
    "@type": "WebSite",
    "@id": absolute(site, localePath(locale)) + "#website",
    name: "Wemute",
    url: absolute(site, localePath(locale)),
    inLanguage: HTML_LANG[locale],
    description,
    publisher: { "@id": absolute(site, "/") + ORGANIZATION_ID },
  };
}

export function breadcrumbs(site: URL, items: { name: string; path: string }[]) {
  return {
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: absolute(site, item.path),
    })),
  };
}

export function toolApplication(site: URL, tool: Tool, locale: Locale) {
  return {
    "@type": "WebApplication",
    name: `${tool.name[locale]} — Wemute`,
    url: absolute(site, localePath(locale, tool.slug)),
    description: tool.metaDescription[locale],
    applicationCategory: "MultimediaApplication",
    operatingSystem: "Any (web browser)",
    browserRequirements: "Requires JavaScript and WebAssembly",
    inLanguage: HTML_LANG[locale],
    isAccessibleForFree: true,
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    publisher: { "@id": absolute(site, "/") + ORGANIZATION_ID },
  };
}

export function howTo(tool: Tool, locale: Locale) {
  return {
    "@type": "HowTo",
    name: tool.h1[locale],
    description: tool.answer[locale],
    totalTime: "PT1M",
    tool: { "@type": "HowToTool", name: "Wemute" },
    step: tool.steps.map((step, index) => ({
      "@type": "HowToStep",
      position: index + 1,
      text: step[locale],
    })),
  };
}

export function faqPage(faqs: { q: Record<Locale, string>; a: Record<Locale, string> }[], locale: Locale) {
  return {
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.q[locale],
      acceptedAnswer: { "@type": "Answer", text: faq.a[locale] },
    })),
  };
}

export function graph(...nodes: object[]) {
  return JSON.stringify({ "@context": "https://schema.org", "@graph": nodes }).replace(/</g, "\\u003c");
}
