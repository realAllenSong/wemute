import type { Category } from "../../data/tools";
import type { UiStrings } from "../../data/ui";
import type { ImageOptions } from "../../lib/image";
import type { GifOptions, VideoCompressOptions } from "../../lib/media";
import type { ConverterTool } from "./Converter";

interface Props {
  strings: UiStrings;
  tool?: ConverterTool;
  kinds: Set<Category>;
  image: ImageOptions;
  gif: GifOptions;
  compress: VideoCompressOptions;
  onImage: (next: ImageOptions) => void;
  onGif: (next: GifOptions) => void;
  onCompress: (next: VideoCompressOptions) => void;
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

function NumberField({
  label,
  value,
  unit,
  min,
  max,
  step = 1,
  placeholder,
  onChange,
}: {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  step?: number;
  placeholder?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="cv-field">
      <span className="cv-field__label">{label}</span>
      <span className="cv-number">
        <input
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          value={value || ""}
          placeholder={placeholder}
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

export function Options({ strings, tool, kinds, image, gif, compress, onImage, onGif, onCompress }: Props) {
  const mode = tool?.mode;
  const showImage = kinds.has("image");
  const showCorners = mode === "image-corners";
  const showTarget = mode === "image-target-size" || mode === "image-compress" || !tool;
  const showGif = kinds.has("video") && (mode === "video-gif" || !tool);
  const showCompress = mode === "video-compress";

  return (
    <div className="cv-options">
      {showImage && (
        <div className="cv-options__group">
          {mode !== "image-corners" && (
            <Segmented
              label={strings.quality}
              value={image.quality}
              options={[
                { value: "small", label: strings.qualitySmall },
                { value: "balanced", label: strings.qualityBalanced },
                { value: "high", label: strings.qualityHigh },
              ]}
              onChange={(quality) => onImage({ ...image, quality })}
            />
          )}
          <label className="cv-field">
            <span className="cv-field__label">{strings.resize}</span>
            <span className="cv-select">
              <select value={image.resize} onChange={(event) => onImage({ ...image, resize: event.currentTarget.value as ImageOptions["resize"] })}>
                <option value="original">{strings.resizeOriginal}</option>
                <option value="half">{strings.resizeHalf}</option>
                <option value="long-1920">{strings.resizeLong1920}</option>
                <option value="long-1080">{strings.resizeLong1080}</option>
                <option value="custom">{strings.resizeCustom}</option>
              </select>
            </span>
          </label>
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
          {showCorners && (
            <label className="cv-field cv-field--wide">
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
          )}
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
      )}

      {showGif && (
        <div className="cv-options__group">
          <NumberField label={strings.start} value={gif.start} unit={strings.seconds} min={0} max={36000} step={0.5} placeholder="0" onChange={(start) => onGif({ ...gif, start })} />
          <NumberField label={strings.length} value={gif.length} unit={strings.seconds} min={0.5} max={60} step={0.5} onChange={(length) => onGif({ ...gif, length: length || 1 })} />
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
      )}

      {showCompress && (
        <div className="cv-options__group">
          <Segmented
            label={strings.quality}
            value={compress.quality}
            options={[
              { value: "small", label: strings.qualitySmall },
              { value: "balanced", label: strings.qualityBalanced },
              { value: "high", label: strings.qualityHigh },
            ]}
            onChange={(quality) => onCompress({ ...compress, quality })}
          />
          <Segmented
            label={strings.maxResolution}
            value={compress.maxHeight}
            options={[
              { value: 0 as const, label: strings.original },
              { value: 1080 as const, label: "1080p" },
              { value: 720 as const, label: "720p" },
              { value: 480 as const, label: "480p" },
            ]}
            onChange={(maxHeight) => onCompress({ ...compress, maxHeight })}
          />
        </div>
      )}
    </div>
  );
}
