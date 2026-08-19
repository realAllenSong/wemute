import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowDown, faImages } from "@fortawesome/free-solid-svg-icons";
import type { Locale } from "../types";
import { t } from "../i18n";

interface EmptyDropStateProps {
  locale: Locale;
  dragging: boolean;
  onChoose: () => void;
}

export function EmptyDropState({ locale, dragging, onChoose }: EmptyDropStateProps) {
  return (
    <section className={`empty-state${dragging ? " empty-state--dragging" : ""}`}>
      <div className="empty-state__icon" aria-hidden="true">
        <FontAwesomeIcon icon={dragging ? faArrowDown : faImages} />
      </div>
      <h1>{t(locale, "dropHere")}</h1>
      <button type="button" className="choose-button" onClick={onChoose}>{t(locale, "chooseFiles")}</button>
      <p>{t(locale, "imageSupport")}</p>
    </section>
  );
}
