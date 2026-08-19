import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowDown, faGlobe } from "@fortawesome/free-solid-svg-icons";
import type { Locale } from "../types";

interface AppHeaderProps {
  locale: Locale;
  compact?: boolean;
  onNavigate: (path: string) => void;
  onToggleLocale: () => void;
}

export function AppHeader({ locale, compact = false, onNavigate, onToggleLocale }: AppHeaderProps) {
  return (
    <header className={`app-header${compact ? " app-header--compact" : ""}`}>
      <button className="brand-button" type="button" onClick={() => onNavigate("/")}>
        <span className="brand-mark" aria-hidden="true"><span /></span>
        <span className="brand">Wemute</span>
      </button>
      {!compact && (
        <nav className="site-nav" aria-label={locale === "en" ? "Primary navigation" : "主导航"}>
          <button type="button" onClick={() => onNavigate("/#tools")}>{locale === "en" ? "Image tools" : "图片工具"}</button>
          <button type="button" onClick={() => onNavigate("/#privacy")}>{locale === "en" ? "Privacy" : "隐私"}</button>
          <button type="button" onClick={() => onNavigate("/#desktop")}>{locale === "en" ? "Desktop app" : "桌面版"}</button>
        </nav>
      )}
      <div className="header-actions">
        <button className="language-button" type="button" onClick={onToggleLocale} aria-label="Change language">
          <FontAwesomeIcon icon={faGlobe} />
          <span>{locale === "en" ? "中文" : "EN"}</span>
        </button>
        {!compact && (
          <button className="header-download" type="button" onClick={() => onNavigate("/#desktop")}>
            {locale === "en" ? "Get Wemute" : "获取 Wemute"}<FontAwesomeIcon icon={faArrowDown} />
          </button>
        )}
      </div>
    </header>
  );
}
