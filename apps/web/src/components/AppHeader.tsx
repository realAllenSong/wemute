import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircle, faEllipsis } from "@fortawesome/free-solid-svg-icons";
import type { Locale } from "../types";

interface AppHeaderProps {
  locale: Locale;
  onToggleLocale: () => void;
}

export function AppHeader({ locale, onToggleLocale }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="traffic-lights" aria-hidden="true">
        <FontAwesomeIcon icon={faCircle} className="traffic-light traffic-light--red" />
        <FontAwesomeIcon icon={faCircle} className="traffic-light traffic-light--yellow" />
        <FontAwesomeIcon icon={faCircle} className="traffic-light traffic-light--green" />
      </div>
      <div className="brand">Wemute <span>Web</span></div>
      <button className="menu-button" type="button" onClick={onToggleLocale} aria-label="Change language">
        <FontAwesomeIcon icon={faEllipsis} />
        <span className="menu-language">{locale === "en" ? "中" : "EN"}</span>
      </button>
    </header>
  );
}
