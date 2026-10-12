declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

type Params = Record<string, string | number>;

/**
 * Count product events. Never pass file names, contents or per-file sizes:
 * only counts, categories and chosen formats.
 */
export function track(event: string, params: Params = {}): void {
  try {
    window.gtag?.("event", event, params);
  } catch {
    // Analytics must never interfere with a conversion.
  }
}
