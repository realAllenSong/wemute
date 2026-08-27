import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faGlobe } from "@fortawesome/free-solid-svg-icons";
import type { Locale } from "../types";

interface AppHeaderProps {
  locale: Locale;
  compact?: boolean;
  onNavigate: (path: string) => void;
  onToggleLocale: () => void;
}

export function AppHeader({ locale, compact = false, onNavigate, onToggleLocale }: AppHeaderProps) {
  const navigate = (event: React.MouseEvent<HTMLAnchorElement>, path: string) => {
    event.preventDefault();
    onNavigate(path);
  };

  return (
    <header className={`app-header${compact ? " app-header--compact" : ""}`}>
      <a className="brand-button" href="/" onClick={(event) => navigate(event, "/")}>
        <img className="brand-icon" src="/wemute-icon-256.png" alt="" width="32" height="32" />
        <span className="brand">Wemute</span>
      </a>
      {!compact && (
        <nav className="site-nav" aria-label={locale === "en" ? "Primary navigation" : "主导航"}>
          <a href="/#tools" onClick={(event) => navigate(event, "/#tools")}>{locale === "en" ? "Image tools" : "图片工具"}</a>
          <a href="/#privacy" onClick={(event) => navigate(event, "/#privacy")}>{locale === "en" ? "How privacy works" : "隐私原理"}</a>
          <a href="/about" onClick={(event) => navigate(event, "/about")}>{locale === "en" ? "About" : "关于"}</a>
        </nav>
      )}
      <div className="header-actions">
        <button className="language-button" type="button" onClick={onToggleLocale} aria-label="Change language">
          <FontAwesomeIcon icon={faGlobe} />
          <span>{locale === "en" ? "中文" : "EN"}</span>
        </button>
        {!compact && (
          <a className="header-download" href="/#tools" onClick={(event) => navigate(event, "/#tools")}>
            {locale === "en" ? "Use a tool" : "开始使用"}<FontAwesomeIcon icon={faArrowRight} />
          </a>
        )}
      </div>
    </header>
  );
}
