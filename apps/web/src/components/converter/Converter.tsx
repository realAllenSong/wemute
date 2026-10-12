import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Category, ImageOutput, MediaOutput, Output, ToolMode } from "../../data/tools";
import type { Locale } from "../../data/locale";
import { format, type UiStrings } from "../../data/ui";
import { track } from "../../lib/analytics";
import { extensionOf, formatBytes, outputName, saveBlob, saveZip, sizeDelta } from "../../lib/files";
import {
  DEFAULT_IMAGE_OPTIONS,
  EXTENSION,
  convertImage,
  isImageFile,
  thumbnail,
  type ImageOptions,
} from "../../lib/image";
import {
  DEFAULT_GIF_OPTIONS,
  DEFAULT_VIDEO_COMPRESS,
  FFMPEG_CORE_SIZE_LABEL,
  convertMedia,
  isAudioFile,
  isFfmpegLoaded,
  isVideoFile,
  loadFfmpeg,
  type GifOptions,
  type VideoCompressOptions,
} from "../../lib/media";
import { audioDuration, formatDuration, videoPreview } from "../../lib/preview";
import { Icon } from "./Icon";
import { Options } from "./Options";

export interface ConverterTool {
  slug: string;
  category: Category;
  mode: ToolMode;
  accept: string;
  output: Output;
  outputs: Output[];
  preset?: Partial<ImageOptions>;
}

interface Props {
  locale: Locale;
  strings: UiStrings;
  tool?: ConverterTool;
}

type Status = "reading" | "ready" | "running" | "done" | "error" | "cancelled";

interface Item {
  id: string;
  file: File;
  kind: Category;
  status: Status;
  progress: number;
  /** Output chosen for this row; undefined follows the group. */
  override?: Output;
  thumb?: string;
  meta: string;
  result?: { blob: Blob; name: string };
  error?: string;
}

const DEFAULT_OUTPUTS: Record<Category, { output: Output; outputs: Output[] }> = {
  image: { output: "jpeg", outputs: ["jpeg", "png", "webp"] },
  video: { output: "mp4", outputs: ["mp4", "gif", "mp3"] },
  audio: { output: "mp3", outputs: ["mp3", "wav", "m4a"] },
};

const OUTPUT_LABEL: Record<Output, string> = {
  jpeg: "JPG",
  png: "PNG",
  webp: "WebP",
  auto: "",
  keep: "",
  mp3: "MP3",
  wav: "WAV",
  m4a: "M4A",
  mp4: "MP4",
  gif: "GIF",
};

const KIND_ICON = { image: "image", video: "film", audio: "music" } as const;
const KINDS: Category[] = ["image", "video", "audio"];

let nextId = 0;

function kindOf(file: File): Category | undefined {
  if (isImageFile(file)) return "image";
  if (isVideoFile(file)) return "video";
  if (isAudioFile(file)) return "audio";
  return undefined;
}

function acceptsKind(tool: ConverterTool | undefined, kind: Category): boolean {
  if (!tool || tool.category === kind) return true;
  // Audio extraction tools also take audio files, e.g. M4A on MP4 → MP3.
  return tool.mode === "media-convert" && tool.category === "video" && kind === "audio" && ["mp3", "m4a", "wav"].includes(tool.output);
}

function errorMessage(error: unknown, locale: Locale): string {
  const code = error instanceof Error ? error.message : "";
  const zh = locale === "zh";
  if (code === "heic") return zh ? "无法解码这个 HEIC 文件" : "This HEIC file couldn't be decoded";
  if (code === "decode") return zh ? "浏览器无法读取这个图片" : "Your browser can't read this image";
  if (code === "encode-unsupported") return zh ? "当前浏览器无法输出该格式" : "This browser can't save this format";
  if (code === "target") return zh ? "无法压缩到目标大小" : "Couldn't reach the target size";
  if (code === "no-audio") return zh ? "这个文件没有可提取的音频" : "This file has no audio track to convert";
  if (code === "engine") return zh ? "转换引擎加载失败，请检查网络后重试" : "The converter engine couldn't load — check your connection";
  return zh ? "转换失败" : "Conversion failed";
}

export default function Converter({ locale, strings, tool }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const itemsRef = useRef<Item[]>([]);
  itemsRef.current = items;

  const [groupOutput, setGroupOutput] = useState<Record<Category, Output>>(() => ({
    image: tool?.category === "image" ? tool.output : DEFAULT_OUTPUTS.image.output,
    video: tool?.category === "video" ? tool.output : DEFAULT_OUTPUTS.video.output,
    audio: tool?.category === "audio" ? tool.output : DEFAULT_OUTPUTS.audio.output,
  }));
  const [imageOptions, setImageOptions] = useState<ImageOptions>(() => ({ ...DEFAULT_IMAGE_OPTIONS, ...tool?.preset }));
  const [gifOptions, setGifOptions] = useState<GifOptions>(DEFAULT_GIF_OPTIONS);
  const [compressOptions, setCompressOptions] = useState<VideoCompressOptions>(DEFAULT_VIDEO_COMPRESS);
  // Tools whose result depends on settings open with their options visible.
  const [showOptions, setShowOptions] = useState(() => tool?.mode === "video-gif" || tool?.mode === "video-compress");
  const [running, setRunning] = useState(false);
  const [engine, setEngine] = useState<{ loading: boolean; progress: number }>({ loading: false, progress: 0 });
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const stopRef = useRef(false);

  // Video tools wait for the user to set options; everything else starts on drop.
  const autoStart = Boolean(tool) && tool?.category !== "video";
  const accept = tool?.accept ?? "image/*,video/*,audio/*,.heic,.heif,.mov,.mkv,.m4a,.flac";

  const outputsFor = useCallback(
    (kind: Category): Output[] => (tool && tool.category === kind ? tool.outputs : DEFAULT_OUTPUTS[kind].outputs),
    [tool],
  );
  const targetOf = useCallback((item: Item): Output => item.override ?? groupOutput[item.kind], [groupOutput]);

  const labelFor = (output: Output) =>
    output === "auto" || output === "keep" ? strings.keepType : OUTPUT_LABEL[output];

  const update = useCallback((id: string, patch: Partial<Item>) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  // ── adding files ──────────────────────────────────────────────────────

  const addFiles = useCallback(
    (list: FileList | File[]) => {
      const files = Array.from(list);
      const accepted: Item[] = [];
      const rejected: string[] = [];
      for (const file of files) {
        const kind = kindOf(file);
        if (!kind || !acceptsKind(tool, kind)) {
          rejected.push(file.name);
          continue;
        }
        accepted.push({
          id: `f${++nextId}`,
          file,
          kind,
          status: "reading",
          progress: 0,
          meta: formatBytes(file.size),
        });
      }
      setNotice(rejected.length ? `${strings.unsupported}: ${rejected.slice(0, 3).join(", ")}${rejected.length > 3 ? "…" : ""}` : "");
      if (!accepted.length) return;
      track("files_added", { file_count: accepted.length, tool: tool?.slug ?? "home" });
      setItems((current) => [...current, ...accepted]);

      for (const item of accepted) {
        const read =
          item.kind === "image"
            ? thumbnail(item.file).then((preview) => ({
                thumb: preview.url,
                meta: `${formatBytes(item.file.size)} · ${preview.width} × ${preview.height}`,
              }))
            : item.kind === "video"
              ? videoPreview(item.file).then((preview) => ({
                  thumb: preview.url,
                  meta: [formatBytes(item.file.size), preview.width ? `${preview.width} × ${preview.height}` : "", formatDuration(preview.duration)]
                    .filter(Boolean)
                    .join(" · "),
                }))
              : audioDuration(item.file).then((preview) => ({
                  thumb: undefined,
                  meta: [formatBytes(item.file.size), formatDuration(preview.duration)].filter(Boolean).join(" · "),
                }));
        read
          .then((patch) => update(item.id, { ...patch, status: "ready" }))
          .catch((error) => update(item.id, { status: item.kind === "image" ? "error" : "ready", error: item.kind === "image" ? errorMessage(error, locale) : undefined }));
      }
    },
    [locale, strings.unsupported, tool, update],
  );

  // Drop anywhere on the page, and paste files.
  useEffect(() => {
    let depth = 0;
    const hasFiles = (event: DragEvent) => Array.from(event.dataTransfer?.types ?? []).includes("Files");
    const onEnter = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth += 1;
      setDragging(true);
    };
    const onLeave = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const onOver = (event: DragEvent) => {
      if (hasFiles(event)) event.preventDefault();
    };
    const onDrop = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth = 0;
      setDragging(false);
      if (event.dataTransfer?.files.length) addFiles(event.dataTransfer.files);
    };
    const onPaste = (event: ClipboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && /INPUT|TEXTAREA/.test(target.tagName)) return;
      const files = Array.from(event.clipboardData?.files ?? []);
      if (files.length) {
        event.preventDefault();
        addFiles(files);
      }
    };
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("dragover", onOver);
    window.addEventListener("drop", onDrop);
    window.addEventListener("paste", onPaste);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("drop", onDrop);
      window.removeEventListener("paste", onPaste);
    };
  }, [addFiles]);

  useEffect(
    () => () => {
      for (const item of itemsRef.current) if (item.thumb) URL.revokeObjectURL(item.thumb);
    },
    [],
  );

  // ── running ───────────────────────────────────────────────────────────

  const runOne = useCallback(
    async (item: Item) => {
      const target = targetOf(item);
      update(item.id, { status: "running", progress: 0.02, error: undefined, result: undefined });
      try {
        if (item.kind === "image") {
          const result = await convertImage({
            file: item.file,
            output: target as ImageOutput,
            options: imageOptions,
            onProgress: (progress) => update(item.id, { progress }),
          });
          update(item.id, {
            status: "done",
            progress: 1,
            result: { blob: result.blob, name: outputName(item.file.name, EXTENSION[result.format]) },
          });
          return true;
        }
        if (!isFfmpegLoaded()) setEngine({ loading: true, progress: 0 });
        try {
          await loadFfmpeg((progress) => setEngine({ loading: progress < 1, progress }));
        } catch (error) {
          console.error("Wemute: converter engine failed to load", error);
          setEngine({ loading: false, progress: 0 });
          throw new Error("engine");
        }
        setEngine({ loading: false, progress: 1 });
        const controller = new AbortController();
        abortRef.current = controller;
        const mode = tool?.mode === "video-compress" ? "compress" : target === "gif" ? "gif" : "convert";
        const result = await convertMedia({
          file: item.file,
          target: target as MediaOutput,
          mode,
          gif: gifOptions,
          compress: compressOptions,
          signal: controller.signal,
          onProgress: (progress) => update(item.id, { progress }),
        });
        abortRef.current = null;
        update(item.id, {
          status: "done",
          progress: 1,
          result: {
            blob: result.blob,
            name: outputName(item.file.name, result.extension, mode === "compress" ? "-small" : ""),
          },
        });
        return true;
      } catch (error) {
        abortRef.current = null;
        if (stopRef.current || (error instanceof DOMException && error.name === "AbortError")) {
          update(item.id, { status: "cancelled", progress: 0 });
        } else {
          update(item.id, { status: "error", progress: 0, error: errorMessage(error, locale) });
        }
        return false;
      }
    },
    [compressOptions, gifOptions, imageOptions, locale, targetOf, tool?.mode, update],
  );

  const start = useCallback(async () => {
    if (running) return;
    const pending = itemsRef.current.filter((item) => item.status === "ready" || item.status === "cancelled" || item.status === "error");
    if (!pending.length) return;
    stopRef.current = false;
    setRunning(true);
    setNotice("");
    const outputs = new Set(pending.map((item) => targetOf(item)));
    track("conversion_started", {
      file_count: pending.length,
      output_format: outputs.size === 1 ? [...outputs][0] : "mixed",
      tool: tool?.slug ?? "home",
    });

    let succeeded = 0;
    const images = pending.filter((item) => item.kind === "image");
    const media = pending.filter((item) => item.kind !== "image");
    const imageLane = async () => {
      // Two at a time keeps the page responsive while using spare cores.
      const queue = [...images];
      const worker = async () => {
        while (queue.length && !stopRef.current) {
          const next = queue.shift()!;
          if (await runOne(next)) succeeded += 1;
        }
      };
      await Promise.all([worker(), worker()]);
    };
    const mediaLane = async () => {
      for (const item of media) {
        if (stopRef.current) break;
        if (await runOne(item)) succeeded += 1;
      }
    };
    await Promise.all([imageLane(), mediaLane()]);
    setRunning(false);
    track("conversion_completed", {
      attempted_count: pending.length,
      succeeded_count: succeeded,
      failed_count: pending.length - succeeded,
      tool: tool?.slug ?? "home",
    });
  }, [runOne, running, targetOf, tool?.slug]);

  const stop = () => {
    stopRef.current = true;
    abortRef.current?.abort();
  };

  // Auto-start once files have been read on single-purpose tool pages.
  useEffect(() => {
    if (!autoStart || running) return;
    if (items.some((item) => item.status === "reading")) return;
    if (items.some((item) => item.status === "ready")) void start();
  }, [autoStart, items, running, start]);

  // Settings changes make finished results stale.
  const invalidate = useCallback((kind?: Category) => {
    setItems((current) =>
      current.map((item) =>
        (!kind || item.kind === kind) && (item.status === "done" || item.status === "error")
          ? { ...item, status: "ready", progress: 0, result: undefined, error: undefined }
          : item,
      ),
    );
  }, []);

  const setGroup = (kind: Category, output: Output) => {
    setGroupOutput((current) => ({ ...current, [kind]: output }));
    setItems((current) =>
      current.map((item) =>
        item.kind === kind && item.status !== "running"
          ? { ...item, override: undefined, status: item.status === "reading" ? "reading" : "ready", progress: 0, result: undefined, error: undefined }
          : item,
      ),
    );
    track("batch_format_changed", { output_format: output });
  };

  const setRow = (item: Item, output: Output) => {
    update(item.id, {
      override: output === groupOutput[item.kind] ? undefined : output,
      status: item.status === "reading" ? "reading" : "ready",
      progress: 0,
      result: undefined,
      error: undefined,
    });
  };

  const remove = (id: string) => {
    setItems((current) => {
      const target = current.find((item) => item.id === id);
      if (target?.thumb) URL.revokeObjectURL(target.thumb);
      return current.filter((item) => item.id !== id);
    });
  };

  const clear = () => {
    stop();
    for (const item of items) if (item.thumb) URL.revokeObjectURL(item.thumb);
    setItems([]);
    setNotice("");
  };

  // ── derived ───────────────────────────────────────────────────────────

  const done = items.filter((item) => item.status === "done" && item.result);
  const pendingCount = items.filter((item) => item.status === "ready" || item.status === "error" || item.status === "cancelled").length;
  const savedBytes = done.reduce((total, item) => total + item.file.size - (item.result?.blob.size ?? 0), 0);
  const overall = items.length
    ? items.reduce((total, item) => total + (item.status === "done" ? 1 : item.status === "running" ? item.progress : 0), 0) /
      items.length
    : 0;
  const groups = useMemo(() => KINDS.map((kind) => ({ kind, items: items.filter((item) => item.kind === kind) })).filter((group) => group.items.length), [items]);
  const kindsPresent = new Set(items.map((item) => item.kind));

  const downloadAll = async () => {
    if (done.length === 1) saveBlob(done[0].result!.blob, done[0].result!.name);
    else await saveZip(done.map((item) => item.result!), `wemute-${tool?.slug ?? "files"}.zip`);
    track("download_completed", { file_count: done.length, download_type: done.length === 1 ? "file" : "zip" });
  };

  const primary = running
    ? { label: strings.stop, icon: "x" as const, kind: "secondary", action: stop }
    : pendingCount > 0
      ? {
          label: pendingCount === items.length ? strings.convert : format(strings.convertN, { count: pendingCount }),
          icon: "arrow-right" as const,
          kind: "primary",
          action: () => void start(),
        }
      : done.length > 0
        ? {
            label: done.length === 1 ? strings.download : strings.downloadAll,
            icon: "download" as const,
            kind: "primary",
            action: () => void downloadAll(),
          }
        : null;

  const acceptChips = tool
    ? Array.from(new Set(tool.accept.split(",").map((part) => part.trim()).filter((part) => part.startsWith(".")).map((part) => part.slice(1).toUpperCase())))
    : [];

  // ── render ────────────────────────────────────────────────────────────

  return (
    <div className={`cv${dragging ? " cv--dragging" : ""}${items.length ? " cv--active" : ""}`}>
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        multiple
        accept={accept}
        tabIndex={-1}
        onChange={(event) => {
          if (event.currentTarget.files) addFiles(event.currentTarget.files);
          event.currentTarget.value = "";
        }}
      />

      {!items.length ? (
        <button type="button" className="cv-drop" onClick={() => inputRef.current?.click()}>
          <span className="cv-mark" aria-hidden="true">
            <span className="cv-sheet cv-sheet--a" />
            <span className="cv-sheet cv-sheet--b">
              <Icon name={dragging ? "download" : "upload"} size={22} />
            </span>
            <svg className="cv-seam" viewBox="0 0 120 110" aria-hidden="true">
              <path d="M70 36 C 54 42, 66 70, 48 76" />
            </svg>
          </span>
          <span className="cv-drop__title">{dragging ? strings.dropTitleActive : strings.dropTitle}</span>
          <span className="cv-drop__sub">
            {strings.dropOr} <span className="cv-drop__choose">{strings.choose}</span>
          </span>
          {acceptChips.length > 0 && (
            <span className="cv-chips">
              {acceptChips.slice(0, 6).map((chip) => (
                <span key={chip} className="cv-chip">
                  {chip}
                </span>
              ))}
            </span>
          )}
          <span className="cv-drop__privacy">
            <Icon name="lock" size={13} />
            {strings.privacyLine} · {strings.dropPaste}
          </span>
        </button>
      ) : (
        <div className="cv-card">
          {notice && (
            <div className="cv-notice" role="status">
              <Icon name="circle-x" size={15} />
              {notice}
            </div>
          )}
          {engine.loading && (
            <div className="cv-engine" role="status">
              <span>{format(strings.engineLoading, { size: FFMPEG_CORE_SIZE_LABEL })}</span>
              <span className="cv-engine__bar">
                <span style={{ width: `${Math.round(engine.progress * 100)}%` }} />
              </span>
            </div>
          )}

          {showOptions && (
            <Options
              strings={strings}
              tool={tool}
              kinds={kindsPresent}
              image={imageOptions}
              gif={gifOptions}
              compress={compressOptions}
              onImage={(next) => {
                setImageOptions(next);
                invalidate("image");
              }}
              onGif={(next) => {
                setGifOptions(next);
                invalidate("video");
              }}
              onCompress={(next) => {
                setCompressOptions(next);
                invalidate("video");
              }}
            />
          )}

          {groups.map((group) => (
            <section key={group.kind} className="cv-group" aria-label={group.kind}>
              <header className="cv-group__head">
                <span className="cv-group__title">
                  <Icon name={KIND_ICON[group.kind]} size={15} />
                  {strings[`${group.kind}Tools` as "imageTools"]}
                  <span className="cv-count">{group.items.length}</span>
                </span>
                {outputsFor(group.kind).length > 1 && (
                  <label className="cv-group__all">
                    <span>{strings.allTo}</span>
                    <span className="cv-select">
                      <select
                        value={groupOutput[group.kind]}
                        disabled={running}
                        onChange={(event) => setGroup(group.kind, event.currentTarget.value as Output)}
                      >
                        {outputsFor(group.kind).map((output) => (
                          <option key={output} value={output}>
                            {labelFor(output)}
                          </option>
                        ))}
                      </select>
                      <Icon name="chevron-down" size={14} />
                    </span>
                  </label>
                )}
              </header>

              <ul className="cv-rows">
                {group.items.map((item) => {
                  const target = targetOf(item);
                  const delta = item.result ? sizeDelta(item.file.size, item.result.blob.size) : null;
                  return (
                    <li key={item.id} className={`cv-row cv-row--${item.status}`}>
                      <span className="cv-thumb">
                        {item.thumb ? <img src={item.thumb} alt="" /> : <Icon name={KIND_ICON[item.kind]} size={18} />}
                      </span>
                      <span className="cv-name">
                        <strong title={item.file.name}>{item.file.name}</strong>
                        <small>{item.meta}</small>
                      </span>
                      <span className="cv-route">
                        <span className="cv-chip">{extensionOf(item.file.name) || "?"}</span>
                        <span className="cv-seamline" aria-hidden="true">
                          <span
                            style={{
                              width: `${item.status === "done" ? 100 : item.status === "running" ? Math.max(6, item.progress * 100) : 0}%`,
                            }}
                          />
                        </span>
                        <span className="cv-select cv-select--row">
                          <select
                            aria-label={`${strings.allTo}: ${item.file.name}`}
                            value={target}
                            disabled={item.status === "running" || running}
                            onChange={(event) => setRow(item, event.currentTarget.value as Output)}
                          >
                            {outputsFor(item.kind).map((output) => (
                              <option key={output} value={output}>
                                {labelFor(output)}
                              </option>
                            ))}
                          </select>
                          <Icon name="chevron-down" size={14} />
                        </span>
                      </span>
                      <span className="cv-status" aria-live="polite">
                        {item.status === "reading" && <span className="cv-muted">{strings.reading}</span>}
                        {item.status === "ready" && <span className="cv-muted">{strings.queued}</span>}
                        {item.status === "cancelled" && <span className="cv-muted">{strings.cancelled}</span>}
                        {item.status === "running" && <span className="cv-percent">{Math.round(item.progress * 100)}%</span>}
                        {item.status === "done" && item.result && (
                          <span className="cv-result">
                            <Icon name="circle-check" size={15} />
                            <span className="cv-num">{formatBytes(item.result.blob.size)}</span>
                            {delta?.label && <span className={delta.smaller ? "cv-delta cv-delta--good" : "cv-delta"}>{delta.label}</span>}
                          </span>
                        )}
                        {item.status === "error" && (
                          <span className="cv-error" title={item.error}>
                            <Icon name="circle-x" size={15} />
                            <span>{item.error}</span>
                          </span>
                        )}
                      </span>
                      <span className="cv-actions">
                        {item.status === "done" && item.result && (
                          <button
                            type="button"
                            className="cv-icon-btn cv-icon-btn--accent"
                            onClick={() => {
                              saveBlob(item.result!.blob, item.result!.name);
                              track("download_completed", { file_count: 1, download_type: "file" });
                            }}
                            aria-label={`${strings.download} ${item.result.name}`}
                            title={strings.download}
                          >
                            <Icon name="download" size={16} />
                          </button>
                        )}
                        {item.status === "error" && (
                          <button type="button" className="cv-icon-btn" onClick={() => void runOne(item)} aria-label={strings.retry} title={strings.retry}>
                            <Icon name="retry" size={15} />
                          </button>
                        )}
                        <button
                          type="button"
                          className="cv-icon-btn"
                          onClick={() => remove(item.id)}
                          disabled={item.status === "running"}
                          aria-label={`${strings.remove} ${item.file.name}`}
                          title={strings.remove}
                        >
                          <Icon name="x" size={15} />
                        </button>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}

          <footer className="cv-bar">
            {running && (
              <span className="cv-bar__progress" aria-hidden="true">
                <span style={{ width: `${Math.round(overall * 100)}%` }} />
              </span>
            )}
            <div className="cv-bar__tools">
              <button type="button" className="cv-btn cv-btn--ghost" onClick={() => inputRef.current?.click()} disabled={running}>
                <Icon name="plus" size={15} />
                <span>{strings.addMore}</span>
              </button>
              <button
                type="button"
                className={`cv-btn cv-btn--ghost${showOptions ? " is-on" : ""}`}
                onClick={() => setShowOptions((value) => !value)}
                aria-expanded={showOptions}
                disabled={running}
              >
                <Icon name="settings" size={15} />
                <span>{strings.options}</span>
              </button>
              <button type="button" className="cv-btn cv-btn--ghost cv-hide-sm" onClick={clear}>
                <Icon name="trash" size={15} />
                <span>{strings.clear}</span>
              </button>
            </div>
            <div className="cv-bar__main">
              <span className="cv-summary">
                {done.length > 0 && !running && (
                  <>
                    {format(strings.summaryDone, { count: done.length })}
                    {savedBytes > 0 && <> · {format(strings.summarySaved, { size: formatBytes(savedBytes) })}</>}
                  </>
                )}
                {running && <span className="cv-percent">{Math.round(overall * 100)}%</span>}
              </span>
              {done.length > 1 && pendingCount > 0 && !running && (
                <button type="button" className="cv-btn cv-btn--secondary" onClick={() => void downloadAll()}>
                  <Icon name="download" size={15} />
                  <span>{strings.downloadAll}</span>
                </button>
              )}
              {primary && (
                <button type="button" className={`cv-btn cv-btn--${primary.kind}`} onClick={primary.action}>
                  <Icon name={primary.icon} size={15} />
                  <span>{primary.label}</span>
                </button>
              )}
            </div>
          </footer>
        </div>
      )}

      {dragging && items.length > 0 && (
        <div className="cv-overlay" aria-hidden="true">
          <span>
            <Icon name="download" size={18} />
            {strings.dropTitleActive}
          </span>
        </div>
      )}
    </div>
  );
}
