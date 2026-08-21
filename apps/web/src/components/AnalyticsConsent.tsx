import { useState } from "react";
import { analyticsConfigured, analyticsConsent, setAnalyticsConsent } from "../lib/analytics";
import type { Locale } from "../types";

interface AnalyticsConsentProps {
  locale: Locale;
  onNavigate: (path: string) => void;
}

export function AnalyticsConsent({ locale, onNavigate }: AnalyticsConsentProps) {
  const [choice, setChoice] = useState(() => analyticsConsent());
  if (!analyticsConfigured || choice !== "unknown") return null;

  const choose = (value: "granted" | "denied") => {
    setAnalyticsConsent(value);
    setChoice(value);
  };

  return (
    <aside className="consent-panel" aria-label={locale === "en" ? "Analytics preference" : "分析偏好"}>
      <div>
        <strong>{locale === "en" ? "Help improve Wemute?" : "帮助改进 Wemute？"}</strong>
        <p>{locale === "en"
          ? "Allow anonymous usage analytics. Filenames and image contents are never included."
          : "允许匿名使用分析。文件名和图片内容绝不会被收集。"}</p>
        <button type="button" onClick={() => onNavigate("/privacy")}>{locale === "en" ? "Privacy details" : "隐私详情"}</button>
      </div>
      <div className="consent-panel__actions">
        <button type="button" onClick={() => choose("denied")}>{locale === "en" ? "No thanks" : "不用了"}</button>
        <button type="button" className="consent-accept" onClick={() => choose("granted")}>{locale === "en" ? "Allow" : "允许"}</button>
      </div>
    </aside>
  );
}
