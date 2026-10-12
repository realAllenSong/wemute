export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${index === 0 ? value : value.toFixed(value >= 100 ? 0 : 1)} ${units[index]}`;
}

/** Signed size change, e.g. "−73%" or "+12%". */
export function sizeDelta(before: number, after: number): { label: string; smaller: boolean } {
  if (!before) return { label: "", smaller: false };
  const change = Math.round((after / before - 1) * 100);
  if (change === 0) return { label: "", smaller: false };
  return change < 0 ? { label: `−${Math.abs(change)}%`, smaller: true } : { label: `+${change}%`, smaller: false };
}

export function baseName(name: string): string {
  const dot = name.lastIndexOf(".");
  return (dot > 0 ? name.slice(0, dot) : name).trim() || "file";
}

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot + 1).toUpperCase() : "";
}

/** Output name next to the source; a same-extension result gets a suffix. */
export function outputName(source: string, extension: string, suffix = ""): string {
  const base = baseName(source);
  const same = extensionOf(source).toLowerCase() === extension.toLowerCase();
  return `${base}${suffix || (same ? "-wemute" : "")}.${extension}`;
}

/** Make names unique within one ZIP: "a.jpg", "a (2).jpg", … */
export function uniqueNames(names: string[]): string[] {
  const seen = new Map<string, number>();
  return names.map((name) => {
    const key = name.toLowerCase();
    const count = (seen.get(key) ?? 0) + 1;
    seen.set(key, count);
    if (count === 1) return name;
    const dot = name.lastIndexOf(".");
    return dot > 0 ? `${name.slice(0, dot)} (${count})${name.slice(dot)}` : `${name} (${count})`;
  });
}

export function saveBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export async function saveZip(files: { blob: Blob; name: string }[], zipName: string): Promise<void> {
  const { zip } = await import("fflate");
  const names = uniqueNames(files.map((file) => file.name));
  const entries: Record<string, [Uint8Array, { level: 0 }]> = {};
  await Promise.all(
    files.map(async (file, index) => {
      // Media is already compressed; storing avoids slow, useless deflate.
      entries[names[index]] = [new Uint8Array(await file.blob.arrayBuffer()), { level: 0 }];
    }),
  );
  const data = await new Promise<Uint8Array>((resolve, reject) =>
    zip(entries, (error, result) => (error ? reject(error) : resolve(result))),
  );
  saveBlob(new Blob([data as Uint8Array<ArrayBuffer>], { type: "application/zip" }), zipName);
}
