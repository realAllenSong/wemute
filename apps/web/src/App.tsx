import { useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear, faLayerGroup, faShieldHalved, faTrashCan } from "@fortawesome/free-solid-svg-icons";
import { AppHeader } from "./components/AppHeader";
import { EmptyDropState } from "./components/EmptyDropState";
import { FileRow } from "./components/FileRow";
import { FormatSelect } from "./components/FormatSelect";
import { OptionsPopover } from "./components/OptionsPopover";
import { useImageQueue } from "./hooks/use-image-queue";
import { defaultLocale, t } from "./i18n";
import type { ConversionOptions, Locale } from "./types";

const INITIAL_OPTIONS: ConversionOptions = {
  quality: "balanced",
  resize: "original",
  customWidth: 1920,
  cornerRadius: 0,
};

export function App() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [locale, setLocale] = useState<Locale>(() => defaultLocale());
  const [options, setOptions] = useState(INITIAL_OPTIONS);
  const [showOptions, setShowOptions] = useState(false);
  const [dragDepth, setDragDepth] = useState(0);
  const queue = useImageQueue(options);
  const allDone = queue.items.length > 0 && queue.items.every((item) => item.status === "done");

  const chooseFiles = () => inputRef.current?.click();
  const addDroppedFiles = (files: FileList) => {
    queue.addFiles(files);
    setDragDepth(0);
  };

  return (
    <div
      className={`app-shell${dragDepth > 0 ? " app-shell--dragging" : ""}`}
      onDragEnter={(event) => {
        event.preventDefault();
        setDragDepth((depth) => depth + 1);
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setDragDepth((depth) => Math.max(0, depth - 1));
      }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        addDroppedFiles(event.dataTransfer.files);
      }}
    >
      <AppHeader locale={locale} onToggleLocale={() => setLocale(locale === "en" ? "zh" : "en")} />
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        multiple
        accept="image/*,.heic,.heif"
        onChange={(event) => {
          if (event.currentTarget.files) queue.addFiles(event.currentTarget.files);
          event.currentTarget.value = "";
        }}
      />

      {queue.items.length === 0 ? (
        <main className="workspace workspace--empty">
          <EmptyDropState locale={locale} dragging={dragDepth > 0} onChoose={chooseFiles} />
        </main>
      ) : (
        <>
          <main className="workspace">
            <div className="queue-summary">
              <div><strong>{queue.items.length}</strong> {t(locale, "files")}</div>
              <div className="summary-actions">
                <button type="button" onClick={queue.clear} disabled={queue.isConverting}>
                  <FontAwesomeIcon icon={faTrashCan} />{t(locale, "clearAll")}
                </button>
                <button type="button" className="text-action" onClick={chooseFiles}>{t(locale, "addFiles")}</button>
              </div>
            </div>

            <section className="file-group" aria-labelledby="images-heading">
              <div className="group-heading">
                <h2 id="images-heading">{t(locale, "images")}</h2>
                <FormatSelect
                  compact
                  label={t(locale, "allTo")}
                  value={queue.groupFormat}
                  disabled={queue.isConverting}
                  onChange={queue.setGroupFormat}
                />
              </div>
              <div className="file-list">
                {queue.items.map((item) => (
                  <FileRow
                    key={item.id}
                    item={item}
                    locale={locale}
                    disabled={queue.isConverting}
                    onRemove={queue.remove}
                    onTargetChange={queue.setTarget}
                  />
                ))}
              </div>
            </section>
          </main>

          <footer className="action-bar">
            <div className="action-bar__left">
              <div className="local-note"><FontAwesomeIcon icon={faShieldHalved} /><span>{t(locale, "browserNote")}</span></div>
              <div className="output-summary">
                <FontAwesomeIcon icon={faLayerGroup} />
                <span>{queue.totalSourceLabel}{queue.outputFiles.length > 0 ? ` → ${queue.totalOutputLabel}` : ""}</span>
              </div>
            </div>
            <div className="action-bar__actions">
              <div className="options-anchor">
                <button
                  type="button"
                  className={`secondary-button${showOptions ? " secondary-button--active" : ""}`}
                  aria-expanded={showOptions}
                  disabled={queue.isConverting}
                  onClick={() => setShowOptions((visible) => !visible)}
                >
                  <FontAwesomeIcon icon={faGear} />{t(locale, "options")}
                </button>
                {showOptions && <OptionsPopover locale={locale} options={options} onChange={setOptions} />}
              </div>
              <button
                type="button"
                className="primary-button"
                disabled={queue.isConverting || queue.readyCount === 0}
                onClick={queue.convertAll}
              >
                {allDone ? t(locale, "downloadAll") : t(locale, "convertAll")}
              </button>
            </div>
          </footer>
        </>
      )}
    </div>
  );
}
