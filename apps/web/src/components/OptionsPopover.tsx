import type { ConversionOptions, Locale, QualityPreset, ResizePreset } from "../types";
import { t } from "../i18n";

interface OptionsPopoverProps {
  locale: Locale;
  options: ConversionOptions;
  onChange: (options: ConversionOptions) => void;
}

export function OptionsPopover({ locale, options, onChange }: OptionsPopoverProps) {
  return (
    <div className="options-popover">
      <label>
        <span>{t(locale, "quality")}</span>
        <select
          value={options.quality}
          onChange={(event) => onChange({ ...options, quality: event.currentTarget.value as QualityPreset })}
        >
          <option value="small">{t(locale, "qualitySmall")}</option>
          <option value="balanced">{t(locale, "qualityBalanced")}</option>
          <option value="high">{t(locale, "qualityHigh")}</option>
        </select>
      </label>
      <label>
        <span>{t(locale, "resize")}</span>
        <select
          value={options.resize}
          onChange={(event) => onChange({ ...options, resize: event.currentTarget.value as ResizePreset })}
        >
          <option value="original">{t(locale, "original")}</option>
          <option value="half">{t(locale, "resizeHalf")}</option>
          <option value="long-1920">{t(locale, "resizeLong")}</option>
          <option value="custom">{t(locale, "resizeCustom")}</option>
        </select>
      </label>
      {options.resize === "custom" && (
        <label>
          <span>{t(locale, "resizeCustom")}</span>
          <div className="number-field">
            <input
              type="number"
              min="64"
              max="12000"
              step="1"
              value={options.customWidth}
              onChange={(event) => onChange({ ...options, customWidth: Number(event.currentTarget.value) || 1 })}
            />
            <span>px</span>
          </div>
        </label>
      )}
      <label>
        <span>{t(locale, "cornerRadius")}</span>
        <select
          value={options.cornerRadius}
          onChange={(event) => onChange({ ...options, cornerRadius: Number(event.currentTarget.value) })}
        >
          <option value="0">0 px</option>
          <option value="16">16 px</option>
          <option value="32">32 px</option>
          <option value="64">64 px</option>
        </select>
      </label>
      <p>{t(locale, "browserNote")}</p>
    </div>
  );
}
