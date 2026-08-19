import { zipSync } from "fflate";
import { uniqueOutputNames } from "./files";

export interface DownloadFile {
  name: string;
  blob: Blob;
}

function triggerDownload(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.style.display = "none";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function downloadZip(files: DownloadFile[]): Promise<void> {
  if (files.length === 0) return;
  const names = uniqueOutputNames(files.map((file) => file.name));
  const entries: Record<string, Uint8Array> = {};
  await Promise.all(
    files.map(async (file, index) => {
      entries[names[index]] = new Uint8Array(await file.blob.arrayBuffer());
    }),
  );
  const archive = zipSync(entries, { level: 0 });
  const archiveBuffer = new ArrayBuffer(archive.byteLength);
  new Uint8Array(archiveBuffer).set(archive);
  triggerDownload(new Blob([archiveBuffer], { type: "application/zip" }), "Wemute Images.zip");
}
