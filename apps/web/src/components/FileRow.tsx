import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faCheckCircle, faCircleExclamation, faClock, faXmark } from "@fortawesome/free-solid-svg-icons";
import { t } from "../i18n";
import { formatBytes } from "../lib/files";
import type { Locale, OutputFormat, QueueImage } from "../types";
import { FormatSelect } from "./FormatSelect";

interface FileRowProps {
  item: QueueImage;
  locale: Locale;
  disabled: boolean;
  onRemove: (id: string) => void;
  onTargetChange: (id: string, format: OutputFormat) => void;
}

export function FileRow({ item, locale, disabled, onRemove, onTargetChange }: FileRowProps) {
  const outputSize = item.outputBlob ? formatBytes(item.outputBlob.size) : undefined;
  const reduction = item.outputBlob && item.file.size > 0
    ? Math.round((1 - item.outputBlob.size / item.file.size) * 100)
    : 0;

  return (
    <article className={`file-row file-row--${item.status}`}>
      <div className="thumbnail-frame">
        <img src={item.sourceUrl} alt="" />
      </div>
      <div className="file-details">
        <h3 title={item.file.name}>{item.file.name}</h3>
        <p>
          {formatBytes(item.file.size)}
          {item.width > 0 && <><span aria-hidden="true">•</span>{item.width} × {item.height}</>}
        </p>
      </div>
      <FontAwesomeIcon icon={faArrowRight} className="row-arrow" aria-hidden="true" />
      <FormatSelect
        value={item.targetFormat}
        disabled={disabled || item.status === "preparing"}
        onChange={(format) => onTargetChange(item.id, format)}
      />
      <div className="file-status" role="status">
        {item.status === "preparing" && (
          <><FontAwesomeIcon icon={faClock} /><div><strong>{t(locale, "preparing")}</strong></div></>
        )}
        {item.status === "ready" && (
          <><FontAwesomeIcon icon={faClock} /><div><strong>{t(locale, "ready")}</strong><span>{t(locale, "readyHint")}</span></div></>
        )}
        {item.status === "converting" && (
          <div className="status-progress">
            <div className="status-progress__copy"><strong>{t(locale, "converting")}</strong><span>{item.progress}%</span></div>
            <div className="linear-progress"><span style={{ width: `${item.progress}%` }} /></div>
          </div>
        )}
        {item.status === "done" && (
          <><FontAwesomeIcon icon={faCheckCircle} className="status-icon--success" /><div><strong>{t(locale, "completed")}</strong><span>{formatBytes(item.file.size)} → {outputSize}{reduction > 0 ? ` (${reduction}% smaller)` : ""}</span></div></>
        )}
        {item.status === "error" && (
          <><FontAwesomeIcon icon={faCircleExclamation} className="status-icon--error" /><div><strong>{t(locale, "error")}</strong><span title={item.error}>{item.error}</span></div></>
        )}
      </div>
      <button
        type="button"
        className="remove-button"
        disabled={disabled}
        aria-label={`${t(locale, "remove")} ${item.file.name}`}
        onClick={() => onRemove(item.id)}
      >
        <FontAwesomeIcon icon={faXmark} />
      </button>
    </article>
  );
}
