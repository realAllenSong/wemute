import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { ToolMode } from "../../data/tools";
import type { UiStrings } from "../../data/ui";
import type { ImageOptions } from "../../lib/image";
import type { GifOptions } from "../../lib/media";
import { Icon } from "./Icon";

export type Tone = "image" | "video" | "audio";

/** A word in the sentence that opens a rounded popover below itself. */
export function Pill({
  label,
  tone,
  open,
  disabled,
  ariaLabel,
  onOpenChange,
  children,
}: {
  label: ReactNode;
  tone: Tone;
  open: boolean;
  disabled?: boolean;
  ariaLabel?: string;
  onOpenChange: (open: boolean) => void;
  children?: ReactNode;
}) {
  const wrapRef = useRef<HTMLSpanElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const [shift, setShift] = useState(0);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: PointerEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) onOpenChange(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [onOpenChange, open]);

  // Keep the popover inside the viewport on narrow screens.
  useLayoutEffect(() => {
    if (!open || !popRef.current) {
      setShift(0);
      return;
    }
    const measure = () => {
      const pop = popRef.current;
      if (!pop) return;
      const rect = pop.getBoundingClientRect();
      const left = rect.left - shift;
      const margin = 12;
      const overflow = left + rect.width - (window.innerWidth - margin);
      setShift(overflow > 0 ? -Math.min(overflow, left - margin) : 0);
    };
    measure();
  }, [open, children]);

  if (!children) {
    return <span className={`cv-pill cv-pill--${tone} is-static`}>{label}</span>;
  }

  return (
    <span className="cv-pillwrap" ref={wrapRef}>
      <button
        type="button"
        className={`cv-pill cv-pill--${tone}${open ? " is-open" : ""}`}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={ariaLabel && typeof label === "string" ? `${ariaLabel}: ${label}` : undefined}
        disabled={disabled}
        onClick={() => onOpenChange(!open)}
      >
        <span>{label}</span>
        <i className="cv-chev" aria-hidden="true" />
      </button>
      {open && (
        <div className="cv-pop" ref={popRef} style={{ transform: `translateX(${shift}px)` }}>
          {children}
        </div>
      )}
    </span>
  );
}

export function Menu<T extends string | number>({
  value,
  options,
  onPick,
  footer,
}: {
  value: T;
  options: { value: T; label: string; group?: string }[];
  onPick: (value: T) => void;
  footer?: { label: string; onClick: () => void };
}) {
  // Consecutive options sharing a group become one titled column.
  const sections: { group?: string; options: typeof options }[] = [];
  for (const option of options) {
    const last = sections[sections.length - 1];
    if (last && last.group === option.group) last.options.push(option);
    else sections.push({ group: option.group, options: [option] });
  }
  const grouped = sections.some((section) => section.group);
  return (
    <div className={`cv-menu${grouped ? " cv-menu--grouped" : ""}`} role="menu">
      {sections.map((section, index) => (
        <div key={index} className={`cv-menu__sec${section.group ? "" : " cv-menu__sec--wide"}`} role={section.group ? "group" : undefined} aria-label={section.group}>
          {section.group && (
            <span className="cv-menu__group" aria-hidden="true">
              {section.group}
            </span>
          )}
          {section.options.map((option) => (
            <button
              key={String(option.value)}
              type="button"
              role="menuitemradio"
              aria-checked={option.value === value}
              className="cv-menu__item"
              onClick={() => onPick(option.value)}
            >
              <span>{option.label}</span>
              {option.value === value && <Icon name="check" size={16} />}
            </button>
          ))}
        </div>
      ))}
      {footer && (
        <>
          <span className="cv-menu__sep" role="separator" />
          <button type="button" role="menuitem" className="cv-menu__item cv-menu__item--more" onClick={footer.onClick}>
            <span>{footer.label}</span>
            <Icon name="settings" size={15} />
          </button>
        </>
      )}
    </div>
  );
}

function Segmented<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="cv-field">
      <span className="cv-field__label">{label}</span>
      <div className="cv-seg" role="radiogroup" aria-label={label}>
        {options.map((option) => (
          <button
            key={String(option.value)}
            type="button"
            role="radio"
            aria-checked={option.value === value}
            className={option.value === value ? "is-on" : ""}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function NumberField({
  label,
  value,
  unit,
  min,
  max,
  step = 1,
  placeholder,
  autoFocus,
  onChange,
}: {
  label?: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  step?: number;
  placeholder?: string;
  autoFocus?: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <label className="cv-field">
      {label && <span className="cv-field__label">{label}</span>}
      <span className="cv-number">
        <input
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          value={value || ""}
          placeholder={placeholder}
          autoFocus={autoFocus}
          onChange={(event) => {
            const next = Number(event.currentTarget.value);
            onChange(Number.isFinite(next) ? Math.min(max, Math.max(0, next)) : 0);
          }}
        />
        <span>{unit}</span>
      </span>
    </label>
  );
}

export function resizeOptions(strings: UiStrings): { value: ImageOptions["resize"]; label: string }[] {
  return [
    { value: "original", label: strings.resizeOriginal },
    { value: "half", label: strings.resizeHalf },
    { value: "long-1920", label: strings.resizeLong1920 },
    { value: "long-1080", label: strings.resizeLong1080 },
    { value: "custom", label: strings.resizeCustom },
  ];
}

export function resizeLabel(strings: UiStrings, image: ImageOptions): string {
  if (image.resize === "custom") return `${image.customWidth} px`;
  return resizeOptions(strings).find((option) => option.value === image.resize)?.label ?? "";
}

export function qualityOptions(strings: UiStrings): { value: ImageOptions["quality"]; label: string }[] {
  return [
    { value: "small", label: strings.qualitySmall },
    { value: "balanced", label: strings.qualityBalanced },
    { value: "high", label: strings.qualityHigh },
  ];
}

/** Size choices, plus a width field when "custom" is picked. */
export function ResizePanel({ strings, image, onImage }: { strings: UiStrings; image: ImageOptions; onImage: (next: ImageOptions) => void }) {
  return (
    <div className="cv-sheet">
      <Segmented label={strings.resize} value={image.resize} options={resizeOptions(strings)} onChange={(resize) => onImage({ ...image, resize })} />
      {image.resize === "custom" && (
        <NumberField
          label={strings.width}
          value={image.customWidth}
          unit="px"
          min={1}
          max={20000}
          onChange={(customWidth) => onImage({ ...image, customWidth: customWidth || 1 })}
        />
      )}
    </div>
  );
}

export function TargetPanel({ strings, image, onImage }: { strings: UiStrings; image: ImageOptions; onImage: (next: ImageOptions) => void }) {
  return (
    <div className="cv-sheet">
      <Segmented
        label={strings.targetSize}
        value={image.targetKB}
        options={[100, 200, 500, 1000].map((value) => ({ value, label: `${value} KB` }))}
        onChange={(targetKB) => onImage({ ...image, targetKB })}
      />
      <NumberField
        value={image.targetKB}
        unit="KB"
        min={0}
        max={100000}
        placeholder={strings.targetOff}
        onChange={(targetKB) => onImage({ ...image, targetKB: Math.round(targetKB) })}
      />
    </div>
  );
}

export function CornersPanel({ strings, image, onImage }: { strings: UiStrings; image: ImageOptions; onImage: (next: ImageOptions) => void }) {
  return (
    <div className="cv-sheet">
      <Segmented
        label={strings.corners}
        value={image.cornerRadius}
        options={[0, 24, 48, 64, 120].map((value) => ({ value, label: value ? `${value}` : strings.cornersNone }))}
        onChange={(cornerRadius) => onImage({ ...image, cornerRadius })}
      />
      <label className="cv-field">
        <span className="cv-field__label">
          {strings.corners} <span className="cv-num">{image.cornerRadius} px</span>
        </span>
        <input
          className="cv-range"
          type="range"
          min={0}
          max={240}
          step={4}
          value={image.cornerRadius}
          onChange={(event) => onImage({ ...image, cornerRadius: Number(event.currentTarget.value) })}
        />
      </label>
    </div>
  );
}

/** "More options…" for images; fields that already have their own pill are left out. */
export function ImageOptionsPanel({
  strings,
  mode,
  image,
  onImage,
}: {
  strings: UiStrings;
  mode?: ToolMode;
  image: ImageOptions;
  onImage: (next: ImageOptions) => void;
}) {
  const showQuality = mode !== "image-corners";
  const showResize = mode !== "image-resize";
  const showTarget = mode === "image-compress" || !mode;
  return (
    <div className="cv-sheet">
      {showResize && <Segmented label={strings.resize} value={image.resize} options={resizeOptions(strings)} onChange={(resize) => onImage({ ...image, resize })} />}
      {showResize && image.resize === "custom" && (
        <NumberField
          label={strings.width}
          value={image.customWidth}
          unit="px"
          min={1}
          max={20000}
          onChange={(customWidth) => onImage({ ...image, customWidth: customWidth || 1 })}
        />
      )}
      {showQuality && <Segmented label={strings.quality} value={image.quality} options={qualityOptions(strings)} onChange={(quality) => onImage({ ...image, quality })} />}
      {showTarget && (
        <NumberField
          label={strings.targetSize}
          value={image.targetKB}
          unit="KB"
          min={0}
          max={100000}
          placeholder={strings.targetOff}
          onChange={(targetKB) => onImage({ ...image, targetKB: Math.round(targetKB) })}
        />
      )}
    </div>
  );
}

export function SecondsPanel({
  label,
  value,
  min,
  max,
  presets,
  strings,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  presets: number[];
  strings: UiStrings;
  onChange: (value: number) => void;
}) {
  return (
    <div className="cv-sheet">
      <Segmented label={label} value={value} options={presets.map((preset) => ({ value: preset, label: `${preset}` }))} onChange={onChange} />
      <NumberField value={value} unit={strings.seconds} min={min} max={max} step={0.5} placeholder="0" onChange={onChange} />
    </div>
  );
}

export function GifExtraPanel({ strings, gif, onGif }: { strings: UiStrings; gif: GifOptions; onGif: (next: GifOptions) => void }) {
  return (
    <div className="cv-sheet">
      <Segmented
        label={strings.gifWidth}
        value={gif.width}
        options={[320, 480, 640, 800].map((value) => ({ value, label: `${value}` }))}
        onChange={(width) => onGif({ ...gif, width })}
      />
      <Segmented
        label={strings.fps}
        value={gif.fps}
        options={[8, 12, 15, 24].map((value) => ({ value, label: `${value}` }))}
        onChange={(fps) => onGif({ ...gif, fps })}
      />
    </div>
  );
}
