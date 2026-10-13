import type { MediaOutput } from "../data/tools";

// FFmpeg core is fetched once from a pinned CDN build and cached by the browser.
export const FFMPEG_CORE_VERSION = "0.12.10";
export const FFMPEG_CORE_BASE = `https://cdn.jsdelivr.net/npm/@ffmpeg/core@${FFMPEG_CORE_VERSION}/dist/esm`;
// Transfer size (the CDN compresses the ~32 MB wasm to about 9 MB).
export const FFMPEG_CORE_SIZE_LABEL = "10 MB";
const FFMPEG_WASM_BYTES = 32_232_419;

export interface GifOptions {
  start: number;
  length: number;
  width: number;
  fps: number;
}

export interface VideoCompressOptions {
  quality: "small" | "balanced" | "high";
  maxHeight: 0 | 1080 | 720 | 480;
}

export const DEFAULT_GIF_OPTIONS: GifOptions = { start: 0, length: 6, width: 480, fps: 12 };
export const DEFAULT_VIDEO_COMPRESS: VideoCompressOptions = { quality: "balanced", maxHeight: 720 };

export interface Probe {
  video?: string;
  audio?: string;
  duration?: number;
}

/** Read codec names and duration from FFmpeg's `-i` banner. */
export function parseProbe(log: string): Probe {
  const probe: Probe = {};
  const video = /Stream #\d+:\d+[^:]*: Video: (\w+)/.exec(log);
  const audio = /Stream #\d+:\d+[^:]*: Audio: (\w+)/.exec(log);
  const duration = /Duration: (\d+):(\d+):(\d+(?:\.\d+)?)/.exec(log);
  if (video) probe.video = video[1];
  if (audio) probe.audio = audio[1];
  if (duration) probe.duration = Number(duration[1]) * 3600 + Number(duration[2]) * 60 + Number(duration[3]);
  return probe;
}

const MP4_SAFE_AUDIO = new Set(["aac", "mp3", "alac"]);

/** H.264 (and AAC/MP3 audio) can move into MP4 without re-encoding. */
export function canRemuxToMp4(probe: Probe): boolean {
  if (probe.video !== "h264") return false;
  return !probe.audio || MP4_SAFE_AUDIO.has(probe.audio);
}

const CRF: Record<VideoCompressOptions["quality"], number> = { small: 30, balanced: 26, high: 22 };

export type MediaMode = "convert" | "gif" | "compress";

export function extensionFor(target: MediaOutput, mode: MediaMode): string {
  return mode === "gif" ? "gif" : target;
}

export interface MediaPlan {
  args: string[];
  extension: string;
  mime: string;
  /** Seconds of output, for progress estimates. */
  expectedDuration?: number;
}

export function planMedia(
  input: string,
  output: string,
  target: MediaOutput,
  mode: MediaMode,
  probe: Probe,
  gif: GifOptions = DEFAULT_GIF_OPTIONS,
  compress: VideoCompressOptions = DEFAULT_VIDEO_COMPRESS,
): MediaPlan {
  const base = ["-hide_banner", "-y"];
  if (target === "gif" || mode === "gif") {
    const filters =
      `fps=${gif.fps},scale='min(${gif.width},iw)':-2:flags=lanczos,split[a][b];` +
      `[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`;
    return {
      args: [...base, "-ss", String(gif.start), "-t", String(gif.length), "-i", input, "-filter_complex", filters, "-loop", "0", output],
      extension: "gif",
      mime: "image/gif",
      expectedDuration: gif.length,
    };
  }
  if (target === "mp3") {
    return {
      args: [...base, "-i", input, "-vn", "-map", "0:a:0", "-c:a", "libmp3lame", "-q:a", "2", output],
      extension: "mp3",
      mime: "audio/mpeg",
      expectedDuration: probe.duration,
    };
  }
  if (target === "m4a") {
    return {
      args: [...base, "-i", input, "-vn", "-map", "0:a:0", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output],
      extension: "m4a",
      mime: "audio/mp4",
      expectedDuration: probe.duration,
    };
  }
  if (target === "wav") {
    return {
      args: [...base, "-i", input, "-vn", "-map", "0:a:0", "-c:a", "pcm_s16le", output],
      extension: "wav",
      mime: "audio/wav",
      expectedDuration: probe.duration,
    };
  }
  // MP4
  if (mode !== "compress" && canRemuxToMp4(probe)) {
    return {
      args: [...base, "-i", input, "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy", "-movflags", "+faststart", output],
      extension: "mp4",
      mime: "video/mp4",
      expectedDuration: probe.duration,
    };
  }
  // H.264 with audio MP4 can't hold (Opus, Vorbis, AC-3, PCM…): keep the picture, convert only the sound.
  if (mode !== "compress" && probe.video === "h264") {
    return {
      args: [...base, "-i", input, "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", output],
      extension: "mp4",
      mime: "video/mp4",
      expectedDuration: probe.duration,
    };
  }
  const crf = mode === "compress" ? CRF[compress.quality] : 21;
  const scale =
    mode === "compress" && compress.maxHeight
      ? ["-vf", `scale=-2:'min(${compress.maxHeight},ih)'`]
      : ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"];
  return {
    args: [
      ...base,
      "-i",
      input,
      "-map",
      "0:v:0",
      "-map",
      "0:a:0?",
      ...scale,
      "-c:v",
      "libx264",
      "-preset",
      "veryfast",
      "-crf",
      String(crf),
      "-pix_fmt",
      "yuv420p",
      "-c:a",
      "aac",
      "-b:a",
      "160k",
      "-movflags",
      "+faststart",
      output,
    ],
    extension: "mp4",
    mime: "video/mp4",
    expectedDuration: probe.duration,
  };
}

// ── runtime ──────────────────────────────────────────────────────────────

type FFmpegInstance = import("@ffmpeg/ffmpeg").FFmpeg;

let instance: Promise<FFmpegInstance> | null = null;

/**
 * Fetch to a blob URL while reporting progress. @ffmpeg/util's own helper
 * compares decompressed bytes with the compressed Content-Length and then fails
 * by re-reading the body, so progress is measured against the known size here.
 */
async function blobUrlWithProgress(url: string, type: string, expected: number, onProgress?: (fraction: number) => void) {
  const response = await fetch(url);
  if (!response.ok || !response.body) throw new Error(`fetch ${response.status}`);
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.byteLength;
    onProgress?.(Math.min(0.99, received / expected));
  }
  return URL.createObjectURL(new Blob(chunks as Uint8Array<ArrayBuffer>[], { type }));
}

export function loadFfmpeg(onProgress?: (fraction: number) => void): Promise<FFmpegInstance> {
  if (!instance) {
    instance = (async () => {
      const [{ FFmpeg }, { toBlobURL }] = await Promise.all([import("@ffmpeg/ffmpeg"), import("@ffmpeg/util")]);
      const ffmpeg = new FFmpeg();
      const [coreURL, wasmURL] = await Promise.all([
        toBlobURL(`${FFMPEG_CORE_BASE}/ffmpeg-core.js`, "text/javascript"),
        blobUrlWithProgress(`${FFMPEG_CORE_BASE}/ffmpeg-core.wasm`, "application/wasm", FFMPEG_WASM_BYTES, onProgress),
      ]);
      await ffmpeg.load({ coreURL, wasmURL });
      onProgress?.(1);
      return ffmpeg;
    })();
    instance.catch(() => {
      instance = null;
    });
  }
  return instance;
}

export function isFfmpegLoaded(): boolean {
  return instance !== null;
}

let jobCounter = 0;

export interface MediaJob {
  file: File;
  target: MediaOutput;
  mode: MediaMode;
  gif?: GifOptions;
  compress?: VideoCompressOptions;
  onProgress?: (value: number) => void;
  signal?: AbortSignal;
}

export async function convertMedia(job: MediaJob): Promise<{ blob: Blob; extension: string }> {
  const ffmpeg = await loadFfmpeg();
  const id = ++jobCounter;
  const extension = (job.file.name.split(".").pop() || "bin").toLowerCase().replace(/[^a-z0-9]/g, "") || "bin";
  const input = `in-${id}.${extension}`;
  const { fetchFile } = await import("@ffmpeg/util");
  await ffmpeg.writeFile(input, await fetchFile(job.file));

  // Probe codecs: FFmpeg prints stream info for `-i` and then fails without output.
  let log = "";
  const collect = ({ message }: { message: string }) => {
    log += `${message}\n`;
  };
  ffmpeg.on("log", collect);
  await ffmpeg.exec(["-hide_banner", "-i", input]).catch(() => undefined);
  ffmpeg.off("log", collect);
  const probe = parseProbe(log);
  // FFmpeg happily writes a frameless GIF when seeking past the end.
  if (job.mode === "gif" && probe.duration && (job.gif?.start ?? 0) >= probe.duration) {
    await ffmpeg.deleteFile(input).catch(() => undefined);
    throw new Error("gif-start");
  }

  const output = `out-${id}.${extensionFor(job.target, job.mode)}`;
  const plan = planMedia(input, output, job.target, job.mode, probe, job.gif, job.compress);

  const total = plan.expectedDuration && plan.expectedDuration > 0 ? plan.expectedDuration : undefined;
  const onTime = ({ message }: { message: string }) => {
    const match = /time=(\d+):(\d+):(\d+(?:\.\d+)?)/.exec(message);
    if (!match || !total) return;
    const seconds = Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]);
    job.onProgress?.(Math.min(0.99, seconds / total));
  };
  const onProgress = ({ progress }: { progress: number }) => {
    if (!total && progress > 0 && progress <= 1) job.onProgress?.(Math.min(0.99, progress));
  };
  ffmpeg.on("log", onTime);
  ffmpeg.on("progress", onProgress);
  const abort = () => ffmpeg.terminate();
  job.signal?.addEventListener("abort", abort, { once: true });
  try {
    const code = await ffmpeg.exec(plan.args);
    if (job.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    if (code !== 0) throw new Error(job.target === "mp3" || job.target === "wav" || job.target === "m4a" ? "no-audio" : "ffmpeg");
    const data = await ffmpeg.readFile(output);
    const bytes = typeof data === "string" ? new TextEncoder().encode(data) : data;
    if (!bytes.byteLength) throw new Error("ffmpeg");
    return { blob: new Blob([bytes as Uint8Array<ArrayBuffer>], { type: plan.mime }), extension: plan.extension };
  } finally {
    job.signal?.removeEventListener("abort", abort);
    ffmpeg.off("log", onTime);
    ffmpeg.off("progress", onProgress);
    if (job.signal?.aborted) {
      // terminate() destroys the worker; the next job loads a fresh one.
      instance = null;
    } else {
      await ffmpeg.deleteFile(input).catch(() => undefined);
      await ffmpeg.deleteFile(output).catch(() => undefined);
    }
  }
}

export function isVideoFile(file: File): boolean {
  return file.type.startsWith("video/") || /\.(mp4|mov|m4v|mkv|webm|avi)$/i.test(file.name);
}

export function isAudioFile(file: File): boolean {
  return file.type.startsWith("audio/") || /\.(mp3|wav|m4a|aac|flac|ogg|opus|aiff?)$/i.test(file.name);
}
