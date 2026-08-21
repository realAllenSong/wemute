export type AnalyticsEvent =
  | "batch_format_changed"
  | "conversion_completed"
  | "conversion_started"
  | "download_completed"
  | "files_added"
  | "page_viewed";

type EventProperties = Record<string, string | number | boolean | undefined>;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

const measurementId = import.meta.env.VITE_GA_MEASUREMENT_ID?.trim();
const consentKey = "wemute:analytics-consent";

export const analyticsConfigured = /^G-[A-Z0-9]+$/i.test(measurementId ?? "");

export function analyticsConsent(): "granted" | "denied" | "unknown" {
  if (!analyticsConfigured) return "denied";
  const value = window.localStorage.getItem(consentKey);
  return value === "granted" || value === "denied" ? value : "unknown";
}

export function initializeAnalytics() {
  if (!analyticsConfigured || analyticsConsent() !== "granted") return;
  if (document.querySelector("script[data-wemute-analytics]")) return;

  window.dataLayer = window.dataLayer ?? [];
  window.gtag = (...args: unknown[]) => { window.dataLayer!.push(args); };
  window.gtag("js", new Date());
  window.gtag("config", measurementId, {
    anonymize_ip: true,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    send_page_view: false,
  });

  const script = document.createElement("script");
  script.async = true;
  script.dataset.wemuteAnalytics = "true";
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId!)}`;
  document.head.appendChild(script);
}

export function setAnalyticsConsent(value: "granted" | "denied") {
  window.localStorage.setItem(consentKey, value);
  if (value === "granted") initializeAnalytics();
}

export function track(event: AnalyticsEvent, properties: EventProperties = {}) {
  window.dispatchEvent(new CustomEvent("wemute:analytics", { detail: { event, properties } }));
  if (analyticsConsent() !== "granted") return;
  initializeAnalytics();
  window.gtag?.("event", event, properties);
}

export function trackPageView(path: string, title: string) {
  track("page_viewed", { page_path: path, page_title: title });
  if (analyticsConsent() === "granted") {
    window.gtag?.("event", "page_view", { page_path: path, page_title: title });
  }
}
