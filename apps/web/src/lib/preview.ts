export interface MediaPreview {
  url?: string;
  duration?: number;
  width?: number;
  height?: number;
}

export function formatDuration(seconds?: number): string {
  if (seconds === undefined || !Number.isFinite(seconds)) return "";
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const mm = String(minutes).padStart(hours ? 2 : 1, "0");
  return hours ? `${hours}:${mm}:${String(secs).padStart(2, "0")}` : `${mm}:${String(secs).padStart(2, "0")}`;
}

function withTimeout<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([promise, new Promise<T>((resolve) => window.setTimeout(() => resolve(fallback), ms))]);
}

/** A frame near the start of a video plus its duration and size. */
export function videoPreview(file: File): Promise<MediaPreview> {
  const source = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.preload = "auto";
  video.src = source;

  const work = new Promise<MediaPreview>((resolve) => {
    const done = (preview: MediaPreview) => {
      URL.revokeObjectURL(source);
      video.removeAttribute("src");
      video.load();
      resolve(preview);
    };
    video.addEventListener("error", () => done({}), { once: true });
    video.addEventListener(
      "loadedmetadata",
      () => {
        const meta = { duration: video.duration, width: video.videoWidth, height: video.videoHeight };
        video.addEventListener(
          "seeked",
          () => {
            try {
              const scale = Math.min(1, 160 / Math.max(1, Math.min(video.videoWidth, video.videoHeight)));
              const canvas = document.createElement("canvas");
              canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
              canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
              canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
              canvas.toBlob(
                (blob) => done({ ...meta, url: blob ? URL.createObjectURL(blob) : undefined }),
                "image/jpeg",
                0.78,
              );
            } catch {
              done(meta);
            }
          },
          { once: true },
        );
        video.currentTime = Math.min(0.5, (video.duration || 1) / 4);
      },
      { once: true },
    );
  });
  return withTimeout(work, 6000, {});
}

export function audioDuration(file: File): Promise<MediaPreview> {
  const source = URL.createObjectURL(file);
  const audio = document.createElement("audio");
  audio.preload = "metadata";
  audio.src = source;
  const work = new Promise<MediaPreview>((resolve) => {
    const done = (preview: MediaPreview) => {
      URL.revokeObjectURL(source);
      resolve(preview);
    };
    audio.addEventListener("loadedmetadata", () => done({ duration: audio.duration }), { once: true });
    audio.addEventListener("error", () => done({}), { once: true });
  });
  return withTimeout(work, 4000, {});
}
