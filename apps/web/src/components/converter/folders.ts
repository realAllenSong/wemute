/** Dropped items as entries; must be called synchronously inside the drop handler. */
export function droppedEntries(data: DataTransfer): FileSystemEntry[] {
  return Array.from(data.items)
    .map((item) => (item.kind === "file" ? item.webkitGetAsEntry?.() : null))
    .filter((entry): entry is FileSystemEntry => Boolean(entry));
}

function readAll(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  // readEntries returns at most ~100 entries per call.
  return new Promise((resolve, reject) => {
    const all: FileSystemEntry[] = [];
    const next = () =>
      reader.readEntries((batch) => {
        if (!batch.length) return resolve(all);
        all.push(...batch);
        next();
      }, reject);
    next();
  });
}

/** Every visible file inside the dropped files and folders, depth first. */
export async function filesFromEntries(entries: FileSystemEntry[]): Promise<File[]> {
  const files: File[] = [];
  const walk = async (entry: FileSystemEntry): Promise<void> => {
    if (entry.name.startsWith(".")) return;
    if (entry.isFile) {
      files.push(await new Promise<File>((resolve, reject) => (entry as FileSystemFileEntry).file(resolve, reject)));
    } else if (entry.isDirectory) {
      for (const child of await readAll((entry as FileSystemDirectoryEntry).createReader())) await walk(child);
    }
  };
  for (const entry of entries) await walk(entry);
  return files;
}
