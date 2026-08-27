import { metadataForPath, structuredDataForPath } from "../site-content.js";

function setMeta(selector: string, attributes: Record<string, string>) {
  let element = document.head.querySelector<HTMLMetaElement>(selector);
  if (!element) {
    element = document.createElement("meta");
    document.head.appendChild(element);
  }
  Object.entries(attributes).forEach(([name, value]) => element!.setAttribute(name, value));
}

function productionOrigin(): string {
  const configured = import.meta.env.VITE_SITE_URL?.trim();
  if (configured) {
    try {
      return new URL(configured).origin;
    } catch {
      // A bad optional value should not break the local converter.
    }
  }
  return window.location.origin;
}

export function applyPageMetadata(pathname: string, locale: "en" | "zh" = "en") {
  const metadata = metadataForPath(pathname);
  const origin = productionOrigin();
  const canonicalUrl = new URL(metadata.path, origin).toString();
  const shareImageUrl = new URL("/wemute-icon-256.png", origin).toString();
  document.title = metadata.title;
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";

  setMeta('meta[name="description"]', { name: "description", content: metadata.description });
  setMeta('meta[property="og:title"]', { property: "og:title", content: metadata.title });
  setMeta('meta[property="og:description"]', { property: "og:description", content: metadata.description });
  setMeta('meta[property="og:url"]', { property: "og:url", content: canonicalUrl });
  setMeta('meta[property="og:type"]', { property: "og:type", content: "website" });
  setMeta('meta[property="og:site_name"]', { property: "og:site_name", content: "Wemute" });
  setMeta('meta[property="og:image"]', { property: "og:image", content: shareImageUrl });
  setMeta('meta[property="og:image:alt"]', { property: "og:image:alt", content: "Wemute app icon" });
  setMeta('meta[name="twitter:card"]', { name: "twitter:card", content: "summary" });
  setMeta('meta[name="twitter:title"]', { name: "twitter:title", content: metadata.title });
  setMeta('meta[name="twitter:description"]', { name: "twitter:description", content: metadata.description });
  setMeta('meta[name="twitter:image"]', { name: "twitter:image", content: shareImageUrl });

  let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement("link");
    canonical.rel = "canonical";
    document.head.appendChild(canonical);
  }
  canonical.href = canonicalUrl;

  let schema = document.head.querySelector<HTMLScriptElement>("#wemute-structured-data");
  if (!schema) {
    schema = document.createElement("script");
    schema.id = "wemute-structured-data";
    schema.type = "application/ld+json";
    document.head.appendChild(schema);
  }
  schema.textContent = JSON.stringify(structuredDataForPath(metadata.path, origin)).replace(/</g, "\\u003c");
}
