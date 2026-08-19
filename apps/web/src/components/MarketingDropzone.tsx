import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowDown, faArrowUpFromBracket, faLock } from "@fortawesome/free-solid-svg-icons";
import type { Locale } from "../types";

interface MarketingDropzoneProps {
  locale: Locale;
  dragging: boolean;
  hint?: string;
  onChoose: () => void;
}

export function MarketingDropzone({ locale, dragging, hint, onChoose }: MarketingDropzoneProps) {
  return (
    <section className={`marketing-dropzone${dragging ? " marketing-dropzone--dragging" : ""}`}>
      <div className="marketing-dropzone__icon" aria-hidden="true">
        <FontAwesomeIcon icon={dragging ? faArrowDown : faArrowUpFromBracket} />
      </div>
      <div className="marketing-dropzone__copy">
        <strong>{dragging ? (locale === "en" ? "Drop to begin" : "松开即可开始") : (hint ?? (locale === "en" ? "Drop images here" : "拖入图片"))}</strong>
        <span>{locale === "en" ? "or choose files from your device" : "或从设备中选择文件"}</span>
      </div>
      <button type="button" onClick={onChoose}>{locale === "en" ? "Choose images" : "选择图片"}</button>
      <p><FontAwesomeIcon icon={faLock} />{locale === "en" ? "Private by design · files never leave this device" : "默认保护隐私 · 文件不会离开这台设备"}</p>
    </section>
  );
}
