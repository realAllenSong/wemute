import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import type { Category, ImageOutput, MediaOutput, Output, ToolMode } from "../../data/tools";
import type { Locale } from "../../data/locale";
import { format, type UiStrings } from "../../data/ui";
import { track } from "../../lib/analytics";
import { formatBytes, outputName, saveBlob, saveZip } from "../../lib/files";
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
import { linkFor, linkForSlug, targetsFor, type PickerData } from "../../data/picker";
import { droppedEntries, filesFromEntries } from "./folders";
import { Icon } from "./Icon";
import {
  CornersPanel,
  GifExtraPanel,
  ImageOptionsPanel,
  Menu,
  Pill,
  ResizePanel,
  SecondsPanel,
  TargetPanel,
  qualityOptions,
  resizeLabel,
} from "./Options";

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
  picker: PickerData;
  tool?: ConverterTool;
}

interface DemoCard {
  name: string;
  badge: string;
  tone: Category;
}

const DEMO_TILT = ["-6deg", "4deg", "-3deg", "6deg"];
const DEMO_NAMES: Record<Category, string[]> = {
  image: ["IMG_0412", "IMG_0431", "harbor", "lake"],
  video: ["trip", "clip", "beach", "demo"],
  audio: ["memo", "track01", "demo", "take2"],
};
const FORMAT_NAME: Record<string, string> = { webp: "WebP", webm: "WebM" };
const formatName = (id: string) => FORMAT_NAME[id] ?? id.toUpperCase();

type Status = "reading" | "ready" | "running" | "done" | "error" | "cancelled";
type Phase = "empty" | "ready" | "running" | "done";

interface Item {
  id: string;
  file: File;
  kind: Category;
  status: Status;
  progress: number;
  thumb?: string;
  duration?: string;
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
const TILT = [-4, 2, -2, 3, -3, 1, -2, 4];
const PENDING: Status[] = ["reading", "ready", "cancelled", "error"];

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

/** Splits a "{name}" template into text runs and the given nodes. */
function fill(template: string, parts: Record<string, ReactNode>): ReactNode {
  return template
    .split(/(\{\w+\})/)
    .filter(Boolean)
    .map((chunk, index) => {
      const key = /^\{(\w+)\}$/.exec(chunk)?.[1];
      return <Fragment key={index}>{key ? parts[key] : chunk}</Fragment>;
    });
}

function sameImageOptions(a: ImageOptions, b: ImageOptions): boolean {
  return (
    a.quality === b.quality &&
    a.resize === b.resize &&
    (a.resize !== "custom" || a.customWidth === b.customWidth) &&
    a.cornerRadius === b.cornerRadius &&
    a.targetKB === b.targetKB
  );
}

export default function Converter({ locale, strings, picker, tool }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const itemsRef = useRef<Item[]>([]);
  itemsRef.current = items;

  const [groupOutput, setGroupOutput] = useState<Record<Category, Output>>(() => ({
    image: tool?.category === "image" ? tool.output : DEFAULT_OUTPUTS.image.output,
    video: tool?.category === "video" ? tool.output : DEFAULT_OUTPUTS.video.output,
    audio: tool?.category === "audio" ? tool.output : DEFAULT_OUTPUTS.audio.output,
  }));
  const baseImageOptions = useMemo<ImageOptions>(() => ({ ...DEFAULT_IMAGE_OPTIONS, ...tool?.preset }), [tool?.preset]);
  const [imageOptions, setImageOptions] = useState<ImageOptions>(baseImageOptions);
  const [gifOptions, setGifOptions] = useState<GifOptions>(DEFAULT_GIF_OPTIONS);
  const [compressOptions, setCompressOptions] = useState<VideoCompressOptions>(DEFAULT_VIDEO_COMPRESS);
  const [running, setRunning] = useState(false);
  const [batch, setBatch] = useState<string[]>([]);
  const [engine, setEngine] = useState<{ loading: boolean; progress: number }>({ loading: false, progress: 0 });
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [sheet, setSheet] = useState(false);
  const [homeSource, setHomeSource] = useState("heic");
  const abortRef = useRef<AbortController | null>(null);
  const stopRef = useRef(false);

  // Video tools wait for the user to set options; everything else starts on drop.
  const autoStart = Boolean(tool) && tool?.category !== "video";
  const accept = tool?.accept ?? "image/*,video/*,audio/*,.heic,.heif,.mov,.mkv,.m4a,.flac";

  const outputsFor = useCallback(
    (kind: Category): Output[] => (tool && tool.category === kind ? tool.outputs : DEFAULT_OUTPUTS[kind].outputs),
    [tool],
  );
  const targetOf = useCallback((item: Item): Output => groupOutput[item.kind], [groupOutput]);

  const labelFor = (output: Output) => (output === "auto" || output === "keep" ? strings.keepType : OUTPUT_LABEL[output]);

  const update = useCallback((id: string, patch: Partial<Item>) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const toggle = useCallback((key: string) => (next: boolean) => {
    setSheet(false);
    setOpen(next ? key : null);
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
        accepted.push({ id: `f${++nextId}`, file, kind, status: "reading", progress: 0, meta: formatBytes(file.size) });
      }
      setNotice(rejected.length ? format(strings.unsupported, { names: `${rejected.slice(0, 3).join(", ")}${rejected.length > 3 ? "…" : ""}` }) : "");
      if (!accepted.length) return;
      track("files_added", { file_count: accepted.length, tool: tool?.slug ?? "home" });
      setItems((current) => [...current, ...accepted]);

      for (const item of accepted) {
        const read: Promise<Partial<Item>> =
          item.kind === "image"
            ? thumbnail(item.file, 240).then((preview) => ({
                thumb: preview.url,
                meta: `${formatBytes(item.file.size)} · ${preview.width} × ${preview.height}`,
              }))
            : item.kind === "video"
              ? videoPreview(item.file).then((preview) => ({
                  thumb: preview.url,
                  duration: formatDuration(preview.duration),
                  meta: [formatBytes(item.file.size), preview.width ? `${preview.width} × ${preview.height}` : "", formatDuration(preview.duration)]
                    .filter(Boolean)
                    .join(" · "),
                }))
              : audioDuration(item.file).then((preview) => ({
                  duration: formatDuration(preview.duration),
                  meta: [formatBytes(item.file.size), formatDuration(preview.duration)].filter(Boolean).join(" · "),
                }));
        // A conversion may already have started; only a still-reading file becomes ready.
        read
          .then((patch) =>
            setItems((current) =>
              current.map((entry) =>
                entry.id === item.id ? { ...entry, ...patch, status: entry.status === "reading" ? "ready" : entry.status } : entry,
              ),
            ),
          )
          .catch((error) =>
            setItems((current) =>
              current.map((entry) =>
                entry.id === item.id && entry.status === "reading"
                  ? item.kind === "image"
                    ? { ...entry, status: "error", error: errorMessage(error, locale) }
                    : { ...entry, status: "ready" }
                  : entry,
              ),
            ),
          );
      }
    },
    [locale, strings.unsupported, tool],
  );

  const choose = () => inputRef.current?.click();

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
      if (!hasFiles(event) || !event.dataTransfer) return;
      event.preventDefault();
      depth = 0;
      setDragging(false);
      const files = Array.from(event.dataTransfer.files);
      const entries = droppedEntries(event.dataTransfer);
      if (entries.some((entry) => entry.isDirectory)) void filesFromEntries(entries).then(addFiles, () => addFiles(files));
      else if (files.length) addFiles(files);
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
    const pending = itemsRef.current.filter((item) => PENDING.includes(item.status));
    if (!pending.length) return;
    stopRef.current = false;
    setOpen(null);
    setRunning(true);
    setBatch(pending.map((item) => item.id));
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

  // Settings changes make finished results of that kind stale.
  const invalidate = useCallback((kind: Category) => {
    setItems((current) =>
      current.map((item) =>
        item.kind === kind && (item.status === "done" || item.status === "error")
          ? { ...item, status: "ready", progress: 0, result: undefined, error: undefined }
          : item,
      ),
    );
  }, []);

  const setGroup = (kind: Category, output: Output) => {
    setOpen(null);
    if (output === groupOutput[kind]) return;
    setGroupOutput((current) => ({ ...current, [kind]: output }));
    invalidate(kind);
    track("batch_format_changed", { output_format: output });
  };

  const onImage = (next: ImageOptions) => {
    setImageOptions(next);
    invalidate("image");
  };
  const onGif = (next: GifOptions) => {
    setGifOptions(next);
    invalidate("video");
  };
  const onCompress = (next: VideoCompressOptions) => {
    setCompressOptions(next);
    invalidate("video");
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
    setBatch([]);
    setNotice("");
    setOpen(null);
  };

  // ── derived ───────────────────────────────────────────────────────────

  const phase: Phase = !items.length
    ? "empty"
    : running
      ? "running"
      : items.some((item) => item.status === "reading" || item.status === "ready" || item.status === "cancelled")
        ? "ready"
        : "done";

  const batchSet = useMemo(() => new Set(batch), [batch]);
  const batchItems = items.filter((item) => batchSet.has(item.id));
  const done = items.filter((item) => item.status === "done" && item.result);
  const failed = items.filter((item) => item.status === "error");
  const finishedInBatch = batchItems.filter((item) => item.status === "done" || item.status === "error").length;
  const overall = batchItems.length
    ? batchItems.reduce((total, item) => total + (item.status === "done" || item.status === "error" ? 1 : item.status === "running" ? item.progress : 0), 0) /
      batchItems.length
    : 0;
  const before = done.reduce((total, item) => total + item.file.size, 0);
  const after = done.reduce((total, item) => total + (item.result?.blob.size ?? 0), 0);

  // The sentence describes the files still to convert (or the batch in flight).
  const sentenceItems = phase === "running" ? batchItems : items.filter((item) => item.status !== "done");
  const groups = KINDS.map((kind) => ({ kind, count: sentenceItems.filter((item) => item.kind === kind).length })).filter((group) => group.count);

  const downloadAll = async () => {
    if (done.length === 1) saveBlob(done[0].result!.blob, done[0].result!.name);
    else await saveZip(done.map((item) => item.result!), `wemute-${tool?.slug ?? "files"}.zip`);
    track("download_completed", { file_count: done.length, download_type: done.length === 1 ? "file" : "zip" });
  };

  // ⏎ starts a ready batch when focus isn't in a control.
  useEffect(() => {
    if (phase !== "ready") return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Enter" || open) return;
      const target = event.target as HTMLElement | null;
      if (target && target !== document.body) return;
      event.preventDefault();
      void start();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, phase, start]);

  // ── sentence ──────────────────────────────────────────────────────────

  const locked = phase === "running";
  const mode = tool?.mode;
  const seconds = (value: number) => format(strings.secondsValue, { value });

  const countLabel = (kind: Category, count: number) =>
    format(strings[count === 1 ? (`${kind}One` as const) : (`${kind}Many` as const)], { count });

  /** The format word; `more` is the sheet behind "More options…" in its menu. */
  const formatPill = (kind: Category, more?: ReactNode) => {
    const outputs = outputsFor(kind);
    const key = `${kind}-format`;
    const label = labelFor(groupOutput[kind]);
    if (outputs.length < 2 && !more) return <Pill label={label} tone={kind} open={false} onOpenChange={() => undefined} />;
    return (
      <Pill label={label} tone={kind} open={open === key} disabled={locked} onOpenChange={toggle(key)}>
        {sheet && more ? (
          more
        ) : (
          <Menu
            value={groupOutput[kind]}
            options={outputs.map((output) => ({ value: output, label: labelFor(output) }))}
            onPick={(output) => setGroup(kind, output)}
            footer={more ? { label: strings.moreOptions, onClick: () => setSheet(true) } : undefined}
          />
        )}
      </Pill>
    );
  };

  const optionPill = (key: string, tone: Category, label: string, panel: ReactNode) => (
    <Pill label={label} tone={tone} open={open === key} disabled={locked} onOpenChange={toggle(key)}>
      {panel}
    </Pill>
  );

  const imageSummary = () => {
    const parts: string[] = [];
    if (mode !== "image-resize" && imageOptions.resize !== baseImageOptions.resize) parts.push(resizeLabel(strings, imageOptions));
    if (mode !== "image-corners" && imageOptions.quality !== baseImageOptions.quality)
      parts.push(qualityOptions(strings).find((option) => option.value === imageOptions.quality)?.label ?? "");
    if (mode !== "image-target-size" && imageOptions.targetKB && imageOptions.targetKB !== baseImageOptions.targetKB) parts.push(`≤ ${imageOptions.targetKB} KB`);
    return parts.filter(Boolean).join(" · ");
  };

  const sentenceLine = (kind: Category, count: number) => {
    const countNode = <b className="cv-count">{countLabel(kind, count)}</b>;
    if (kind === "image") {
      const changed = !sameImageOptions(imageOptions, baseImageOptions) && imageSummary();
      const extra = changed
        ? fill(strings.sentExtra, {
            extra: optionPill("image-extra", "image", changed, <ImageOptionsPanel strings={strings} mode={mode} image={imageOptions} onImage={onImage} />),
          })
        : null;
      const formatNode = formatPill("image", <ImageOptionsPanel strings={strings} mode={mode} image={imageOptions} onImage={onImage} />);
      if (mode === "image-target-size")
        return (
          <>
            {fill(strings.sentTarget, {
              count: countNode,
              size: optionPill("image-target", "image", `${imageOptions.targetKB || "—"} KB`, <TargetPanel strings={strings} image={imageOptions} onImage={onImage} />),
              format: formatNode,
            })}
            {extra}
          </>
        );
      if (mode === "image-resize")
        return (
          <>
            {fill(strings.sentResize, {
              count: countNode,
              size: optionPill("image-resize", "image", resizeLabel(strings, imageOptions), <ResizePanel strings={strings} image={imageOptions} onImage={onImage} />),
              format: formatNode,
            })}
            {extra}
          </>
        );
      if (mode === "image-corners")
        return (
          <>
            {fill(strings.sentCorners, {
              count: countNode,
              size: optionPill("image-corners", "image", `${imageOptions.cornerRadius} px`, <CornersPanel strings={strings} image={imageOptions} onImage={onImage} />),
              format: formatNode,
            })}
            {extra}
          </>
        );
      return (
        <>
          {fill(mode === "image-compress" ? strings.sentCompress : strings.sentConvert, { count: countNode, format: formatNode })}
          {extra}
        </>
      );
    }
    if (kind === "video" && mode === "video-compress") {
      const sizes = [
        { value: 0 as const, label: strings.original },
        { value: 1080 as const, label: "1080p" },
        { value: 720 as const, label: "720p" },
        { value: 480 as const, label: "480p" },
      ];
      return fill(strings.sentVideoCompress, {
        count: countNode,
        size: optionPill(
          "video-size",
          "video",
          sizes.find((size) => size.value === compressOptions.maxHeight)?.label ?? "",
          <Menu value={compressOptions.maxHeight} options={sizes} onPick={(maxHeight) => { onCompress({ ...compressOptions, maxHeight }); setOpen(null); }} />,
        ),
        quality: optionPill(
          "video-quality",
          "video",
          qualityOptions(strings).find((option) => option.value === compressOptions.quality)?.label ?? "",
          <Menu value={compressOptions.quality} options={qualityOptions(strings)} onPick={(quality) => { onCompress({ ...compressOptions, quality }); setOpen(null); }} />,
        ),
      });
    }
    if (kind === "video" && groupOutput.video === "gif") {
      return (
        <>
          {fill(strings.sentGif, {
            count: countNode,
            format: formatPill("video", <GifExtraPanel strings={strings} gif={gifOptions} onGif={onGif} />),
            start: optionPill(
              "gif-start",
              "video",
              seconds(gifOptions.start),
              <SecondsPanel strings={strings} label={strings.start} value={gifOptions.start} min={0} max={36000} presets={[0, 1, 2, 5, 10]} onChange={(start) => onGif({ ...gifOptions, start })} />,
            ),
            length: optionPill(
              "gif-length",
              "video",
              seconds(gifOptions.length),
              <SecondsPanel
                strings={strings}
                label={strings.length}
                value={gifOptions.length}
                min={0.5}
                max={60}
                presets={[3, 6, 10, 15]}
                onChange={(length) => onGif({ ...gifOptions, length: length || 1 })}
              />,
            ),
          })}
        </>
      );
    }
    return fill(strings.sentConvert, { count: countNode, format: formatPill(kind) });
  };

  // ── empty sentence: a tool picker before any file is added ────────────

  const go = (href: string) => {
    setOpen(null);
    window.location.assign(href);
  };

  const current = tool ? linkForSlug(picker, tool.slug) : undefined;
  // "" means the tool takes any file of its kind (compress, resize, …).
  const sourceId = tool ? (current?.from ?? "") : homeSource;
  const targetId = tool ? current?.to : targetsFor(picker, homeSource)[0]?.to;
  const sourceKind: Category = tool?.category ?? (picker.sources.find((source) => source.id === sourceId)?.kind as Category | undefined) ?? "image";
  const tone: Category = sourceId === "any" ? "image" : sourceKind;

  const pickSource = (id: string) => {
    setOpen(null);
    if (id === "any") {
      if (tool) go(picker.home);
      else setHomeSource("any");
      return;
    }
    if (tool && id === sourceId) return;
    const link = linkFor(picker, id, targetId);
    if (link) go(link.href);
  };

  const KIND_GROUP: Record<Category, string> = { image: strings.kindImage, video: strings.kindVideo, audio: strings.kindAudio };
  const sourcePill = (
    <Pill
      label={sourceId ? (picker.sources.find((source) => source.id === sourceId)?.label ?? sourceId) : picker.kindSource[sourceKind]}
      tone={tone}
      open={open === "source"}
      ariaLabel={strings.pickSource}
      onOpenChange={toggle("source")}
    >
      <Menu
        value={sourceId}
        options={picker.sources.map((source) => ({ value: source.id, label: source.label, group: source.kind === "any" ? undefined : KIND_GROUP[source.kind] }))}
        onPick={pickSource}
      />
    </Pill>
  );

  const navPill = (label: string, value: string, options: { value: string; label: string; href: string }[]) =>
    options.length < 2 ? (
      <Pill label={label} tone={tone} open={false} onOpenChange={() => undefined} />
    ) : (
      <Pill label={label} tone={tone} open={open === "target"} ariaLabel={strings.pickTarget} onOpenChange={toggle("target")}>
        <Menu
          value={value}
          options={options}
          onPick={(next) => {
            const option = options.find((item) => item.value === next);
            if (!tool || next !== value) go(option!.href);
            else setOpen(null);
          }}
        />
      </Pill>
    );

  const resizePanel = <ResizePanel strings={strings} image={imageOptions} onImage={onImage} />;
  const cornersPanel = <CornersPanel strings={strings} image={imageOptions} onImage={onImage} />;
  const videoSizes = [
    { value: 0 as const, label: strings.original },
    { value: 1080 as const, label: "1080p" },
    { value: 720 as const, label: "720p" },
    { value: 480 as const, label: "480p" },
  ];

  /** The sentence template, its target pill, and the short word shown on the demo cards. */
  const emptyTarget = (): { template: string; pill: ReactNode; badge: string } => {
    if (mode === "image-target-size" || mode === "image-compress") {
      const size = picker.sizes.find((item) => item.slug === tool!.slug);
      return {
        template: strings.sentEmptyCompress,
        pill: navPill(size?.label ?? "", tool!.slug, picker.sizes.map((item) => ({ value: item.slug, label: item.label, href: item.href }))),
        badge: mode === "image-compress" ? strings.qualitySmall : `${imageOptions.targetKB} KB`,
      };
    }
    if (mode === "image-resize")
      return { template: strings.sentEmptyResize, pill: optionPill("empty-resize", "image", resizeLabel(strings, imageOptions), resizePanel), badge: resizeLabel(strings, imageOptions) };
    if (mode === "image-corners")
      return { template: strings.sentEmptyCorners, pill: optionPill("empty-corners", "image", `${imageOptions.cornerRadius} px`, cornersPanel), badge: `${imageOptions.cornerRadius} px` };
    if (mode === "video-compress") {
      const label = videoSizes.find((size) => size.value === compressOptions.maxHeight)?.label ?? "";
      return {
        template: strings.sentEmptyCompress,
        pill: optionPill(
          "empty-video-size",
          "video",
          label,
          <Menu value={compressOptions.maxHeight} options={videoSizes} onPick={(maxHeight) => { onCompress({ ...compressOptions, maxHeight }); setOpen(null); }} />,
        ),
        badge: label,
      };
    }
    if (tool && !current) return { template: strings.sentEmpty, pill: formatPill(tool.category), badge: labelFor(groupOutput[tool.category]) };
    if (sourceId === "any") return { template: strings.sentEmpty, pill: <Pill label={strings.anyTarget} tone="image" open={false} onOpenChange={() => undefined} />, badge: "" };
    const targets = targetsFor(picker, sourceId);
    const target = targets.find((link) => link.to === targetId);
    return {
      template: strings.sentEmpty,
      pill: navPill(target?.label ?? "", targetId ?? "", targets.map((link) => ({ value: link.to, label: link.label, href: link.href }))),
      badge: target?.label ?? "",
    };
  };

  const demoCards = (badge: string): DemoCard[] => {
    if (!tool)
      return [
        { name: "IMG_0412.HEIC", badge: "JPG", tone: "image" },
        { name: "IMG_0431.HEIC", badge: "JPG", tone: "image" },
        { name: "trip.mov", badge: "MP4", tone: "video" },
        { name: "lake.png", badge: "WebP", tone: "image" },
      ];
    const ext = sourceId === "heic" ? "HEIC" : sourceId || { image: "jpg", video: "mp4", audio: "mp3" }[tool.category];
    return DEMO_NAMES[tool.category].map((name) => ({ name: `${name}.${ext}`, badge, tone: tool.category }));
  };

  const dropTitle = (): string => {
    if (dragging) return strings.dropTitleActive;
    if (!tool) return strings.dropTitle;
    if (!autoStart) return strings.toolHintWait;
    if (mode === "image-target-size") return format(strings.toolHintTarget, { size: `${imageOptions.targetKB} KB` });
    if ((mode === "image-convert" || mode === "media-convert") && OUTPUT_LABEL[groupOutput[tool.category]])
      return format(strings.toolHintAuto, { format: OUTPUT_LABEL[groupOutput[tool.category]] });
    return strings.toolHintStart;
  };

  const dropLine = (): string => {
    if (!tool) return strings.dropHint;
    const parts = tool.accept.split(",").map((part) => part.trim());
    const list = parts.every((part) => !part.endsWith("/*"))
      ? Array.from(new Set(parts.filter((part) => part.startsWith(".")))).join(" / ")
      : sourceId
        ? format(strings.dropAlso, { format: formatName(sourceId) })
        : { image: strings.formatsImage, video: strings.formatsVideo, audio: strings.formatsAudio }[tool.category];
    return format(strings.dropFormats, { list });
  };

  const chooseLabel = !tool
    ? strings.chooseFiles
    : { image: strings.chooseImages, video: strings.chooseVideos, audio: strings.chooseAudio }[tool.category];

  // ── render ────────────────────────────────────────────────────────────

  const fileInput = (
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
  );

  if (phase === "empty") {
    const target = emptyTarget();
    const cards = demoCards(target.badge);
    return (
      <div className={`cv${dragging ? " cv--dragging" : ""}`}>
        {fileInput}
        <div className="cv-panel cv-app">
          <div className="cv-head cv-head--empty">
            <p className="cv-sentence">{fill(target.template, { source: sourcePill, target: target.pill })}</p>
            <button type="button" className="cv-go cv-go--choose" onClick={choose}>
              {chooseLabel}
              <Icon name="arrow-right" size={19} />
            </button>
          </div>
          <button type="button" className="cv-stage" onClick={choose}>
            <span className="cv-demos" aria-hidden="true">
              {cards.map((card, index) => (
                <span key={index} className={`cv-demo cv-demo--${index + 1}`} style={{ "--r": DEMO_TILT[index], "--d": `${-index * 1.5}s` } as CSSProperties}>
                  <span className={`cv-demo__ph cv-demo__ph--${card.tone}`}>
                    {card.tone === "audio" ? (
                      <Icon name="music" size={36} />
                    ) : (
                      <img src={`/demo/${index + 1}.webp`} alt="" width={120} height={120} loading="lazy" decoding="async" draggable={false} />
                    )}
                    {card.badge && <span className={`cv-demo__to cv-demo__to--${card.tone}`}>→ {card.badge}</span>}
                  </span>
                  <small>{card.name}</small>
                </span>
              ))}
            </span>
            <span className="cv-drop">
              <strong>{dropTitle()}</strong>
              <span>{dropLine()}</span>
            </span>
          </button>
          {notice && <p className="cv-quiet cv-quiet--error cv-quiet--center">{notice}</p>}
        </div>
      </div>
    );
  }

  const savedBytes = before - after;
  const total = batchItems.length || sentenceItems.length;

  return (
    <div className={`cv${dragging ? " cv--dragging" : ""}`}>
      {fileInput}
      <div className={`cv-panel cv-app cv-work cv-work--${phase}`}>
        {phase === "done" ? (
          <div className="cv-done" aria-live="polite">
            <h2 className="cv-done__title">
              {failed.length
                ? format(strings.doneMixed, { done: done.length, failed: failed.length })
                : done.length === 1
                  ? strings.doneOne
                  : format(strings.doneAll, { count: done.length })}
            </h2>
            {done.length > 0 && (
              <p className="cv-done__line">
                {savedBytes > 0
                  ? fill(strings.savedLine, { size: <em>{formatBytes(savedBytes)}</em> })
                  : fill(strings.totalLine, { size: <b>{formatBytes(after)}</b> })}
              </p>
            )}
            <div className="cv-actions">
              {done.length > 0 && (
                <button type="button" className="cv-go" onClick={() => void downloadAll()}>
                  <Icon name="download" size={18} />
                  <span>{done.length === 1 ? strings.download : strings.downloadAll}</span>
                </button>
              )}
              <button type="button" className="cv-sec" onClick={clear}>
                {strings.again}
              </button>
              {failed.length > 0 && (
                <button type="button" className="cv-retry" onClick={() => void start()}>
                  <Icon name="retry" size={15} />
                  {format(strings.retryFailed, { count: failed.length })}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="cv-head">
            <p className="cv-sentence">
              {groups.map((group) => (
                <span key={group.kind} className="cv-line">
                  {sentenceLine(group.kind, group.count)}
                </span>
              ))}
            </p>
            {phase === "running" ? (
              <div className="cv-run">
                <div className="cv-meter" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(overall * 100)}>
                  <i style={{ width: `${Math.max(3, Math.round(overall * 100))}%` }} />
                </div>
                <div className="cv-row-end">
                  <span className="cv-run__label">{format(strings.progress, { done: finishedInBatch, total })}</span>
                  <button type="button" className="cv-sec cv-sec--quiet" onClick={stop}>
                    {strings.stop}
                  </button>
                </div>
              </div>
            ) : (
              <div className="cv-row-end">
                <span className="cv-tools">
                  <button type="button" className="cv-ghost" onClick={choose}>
                    <Icon name="plus" size={16} />
                    {strings.addMore}
                  </button>
                  <button type="button" className="cv-ghost" onClick={clear}>
                    {strings.clear}
                  </button>
                </span>
                <button type="button" className="cv-go" onClick={() => void start()} disabled={!sentenceItems.length}>
                  {strings.convert}
                  <Icon name="arrow-right" size={18} />
                </button>
              </div>
            )}
          </div>
        )}

        {(notice || engine.loading) && (
          <div className="cv-quiets">
            {engine.loading && (
              <span className="cv-quiet">
                {format(strings.engineLoading, { size: FFMPEG_CORE_SIZE_LABEL })}
                <span className="cv-quiet__bar">
                  <i style={{ width: `${Math.round(engine.progress * 100)}%` }} />
                </span>
              </span>
            )}
            {notice && <span className="cv-quiet cv-quiet--error">{notice}</span>}
          </div>
        )}

        <ul className="cv-cards">
          {items.map((item, index) => (
            <li
              key={item.id}
              className={`cv-card cv-card--${item.kind} is-${item.status}`}
              style={{ "--r": `${TILT[index % TILT.length]}deg` } as CSSProperties}
              title={item.error ? `${item.file.name} — ${item.error}` : `${item.file.name} · ${item.meta}${item.result ? ` → ${formatBytes(item.result.blob.size)}` : ""}`}
            >
              <span className="cv-card__ph">
                {item.thumb ? (
                  <img src={item.thumb} alt="" draggable={false} />
                ) : (
                  <span className={`cv-card__glyph${item.status === "reading" && item.kind === "image" ? " is-loading" : ""}`}>
                    <Icon name={KIND_ICON[item.kind]} size={30} />
                  </span>
                )}
                {item.duration && item.kind === "video" && <span className="cv-card__dur">▶ {item.duration}</span>}
                {item.duration && item.kind === "audio" && <span className="cv-card__dur">{item.duration}</span>}
                {item.status === "done" && <span className="cv-badge cv-badge--ok" aria-label="✓" />}
                {item.status === "error" && (
                  <span className="cv-badge cv-badge--error" aria-label={item.error}>
                    !
                  </span>
                )}
                {item.status === "running" && (
                  <span className="cv-badge cv-badge--run" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="9" />
                      <circle cx="12" cy="12" r="9" style={{ strokeDashoffset: `${56.5 * (1 - item.progress)}` }} />
                    </svg>
                  </span>
                )}
                {item.status === "done" && item.result && (
                  <button
                    type="button"
                    className="cv-card__dl"
                    onClick={() => {
                      saveBlob(item.result!.blob, item.result!.name);
                      track("download_completed", { file_count: 1, download_type: "file" });
                    }}
                    aria-label={`${strings.download} ${item.result.name}`}
                    title={strings.download}
                  >
                    <Icon name="download" size={17} />
                  </button>
                )}
              </span>
              <small className="cv-card__name">{item.status === "done" && item.result ? item.result.name : item.file.name}</small>
              {!locked && (
                <button type="button" className="cv-card__x" onClick={() => remove(item.id)} aria-label={`${strings.remove} ${item.file.name}`} title={strings.remove}>
                  <Icon name="x" size={12} />
                </button>
              )}
            </li>
          ))}
        </ul>

        {dragging && (
          <div className="cv-overlay" aria-hidden="true">
            <span>
              <Icon name="download" size={18} />
              {strings.dropTitleActive}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
