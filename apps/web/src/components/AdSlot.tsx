import { useEffect, useRef } from "react";

declare global {
  interface Window {
    adsbygoogle?: Record<string, unknown>[];
  }
}

interface AdSlotProps {
  locale: "en" | "zh";
  placement: "home" | "tool";
}

const adsenseClient = import.meta.env.VITE_ADSENSE_CLIENT?.trim();
const consentReady = import.meta.env.VITE_ADSENSE_CONSENT_READY === "true";

function slotFor(placement: AdSlotProps["placement"]): string | undefined {
  return (placement === "home"
    ? import.meta.env.VITE_ADSENSE_HOME_SLOT
    : import.meta.env.VITE_ADSENSE_TOOL_SLOT)?.trim();
}

export function AdSlot({ locale, placement }: AdSlotProps) {
  const requested = useRef(false);
  const slot = slotFor(placement);
  const enabled = consentReady
    && /^ca-pub-\d+$/.test(adsenseClient ?? "")
    && /^\d+$/.test(slot ?? "");

  useEffect(() => {
    if (!enabled || requested.current) return;
    requested.current = true;

    if (!document.querySelector("script[data-wemute-adsense]")) {
      const script = document.createElement("script");
      script.async = true;
      script.crossOrigin = "anonymous";
      script.dataset.wemuteAdsense = "true";
      script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(adsenseClient!)}`;
      document.head.appendChild(script);
    }

    window.adsbygoogle = window.adsbygoogle ?? [];
    window.adsbygoogle.push({});
  }, [enabled]);

  if (!enabled) return null;

  return (
    <aside className="ad-slot" aria-label={locale === "en" ? "Advertisement" : "广告"}>
      <span>{locale === "en" ? "Advertisement" : "广告"}</span>
      <ins
        className="adsbygoogle"
        data-ad-client={adsenseClient}
        data-ad-slot={slot}
        data-ad-format="auto"
        data-full-width-responsive="true"
        style={{ display: "block" }}
      />
    </aside>
  );
}
