import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileImage } from "@fortawesome/free-solid-svg-icons";
import { formatLabel } from "../lib/files";
import type { OutputFormat } from "../types";

interface FormatSelectProps {
  value: OutputFormat;
  onChange: (format: OutputFormat) => void;
  label?: string;
  compact?: boolean;
  disabled?: boolean;
}

const formats: OutputFormat[] = ["webp", "jpeg", "png"];

export function FormatSelect({ value, onChange, label, compact, disabled }: FormatSelectProps) {
  return (
    <label className={`format-select${compact ? " format-select--compact" : ""}`}>
      <FontAwesomeIcon icon={faFileImage} aria-hidden="true" />
      {label && <span className="format-select__label">{label}</span>}
      <select
        aria-label={label || "Output format"}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.currentTarget.value as OutputFormat)}
      >
        {formats.map((format) => <option key={format} value={format}>{formatLabel(format)}</option>)}
      </select>
    </label>
  );
}
