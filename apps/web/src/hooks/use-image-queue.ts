import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { downloadZip } from "../lib/download";
import { formatBytes, isImageFile, outputNameFor } from "../lib/files";
import { convertImage, probeImage } from "../lib/image-conversion";
import type { ConversionOptions, OutputFormat, QueueImage } from "../types";

function createId(): string {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useImageQueue(options: ConversionOptions, initialFormat: OutputFormat = "webp") {
  const [items, setItems] = useState<QueueImage[]>([]);
  const [groupFormat, setGroupFormatState] = useState<OutputFormat>(initialFormat);
  const [isConverting, setIsConverting] = useState(false);
  const itemsRef = useRef<QueueImage[]>([]);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    return () => {
      itemsRef.current.forEach((item) => URL.revokeObjectURL(item.sourceUrl));
    };
  }, []);

  useEffect(() => {
    setItems((current) =>
      current.map((item) =>
        item.status === "done"
          ? { ...item, status: "ready", progress: 0, outputBlob: undefined, outputName: undefined }
          : item,
      ),
    );
  }, [options]);

  const addFiles = useCallback(
    (inputFiles: FileList | File[]) => {
      const files = Array.from(inputFiles).filter(isImageFile);
      if (files.length === 0) return;

      const nextItems = files.map<QueueImage>((file) => ({
        id: createId(),
        file,
        sourceUrl: URL.createObjectURL(file),
        width: 0,
        height: 0,
        targetFormat: groupFormat,
        status: "preparing",
        progress: 0,
      }));

      setItems((current) => [...current, ...nextItems]);
      nextItems.forEach(async (item) => {
        try {
          const dimensions = await probeImage(item.file);
          setItems((current) =>
            current.map((candidate) =>
              candidate.id === item.id
                ? { ...candidate, ...dimensions, status: "ready", error: undefined }
                : candidate,
            ),
          );
        } catch (error) {
          setItems((current) =>
            current.map((candidate) =>
              candidate.id === item.id
                ? {
                    ...candidate,
                    status: "error",
                    error: error instanceof Error ? error.message : "Unsupported image",
                  }
                : candidate,
            ),
          );
        }
      });
    },
    [groupFormat],
  );

  const remove = useCallback((id: string) => {
    setItems((current) => {
      const target = current.find((item) => item.id === id);
      if (target) URL.revokeObjectURL(target.sourceUrl);
      return current.filter((item) => item.id !== id);
    });
  }, []);

  const clear = useCallback(() => {
    setItems((current) => {
      current.forEach((item) => URL.revokeObjectURL(item.sourceUrl));
      return [];
    });
  }, []);

  const setTarget = useCallback((id: string, format: OutputFormat) => {
    setItems((current) =>
      current.map((item) =>
        item.id === id
          ? { ...item, targetFormat: format, status: item.status === "preparing" ? "preparing" : "ready", outputBlob: undefined }
          : item,
      ),
    );
  }, []);

  const setGroupFormat = useCallback((format: OutputFormat) => {
    setGroupFormatState(format);
    setItems((current) =>
      current.map((item) => ({
        ...item,
        targetFormat: format,
        status: item.status === "preparing" ? "preparing" : "ready",
        progress: 0,
        outputBlob: undefined,
        outputName: undefined,
        error: undefined,
      })),
    );
  }, []);

  const outputFiles = useMemo(
    () =>
      items.flatMap((item) =>
        item.outputBlob && item.outputName ? [{ blob: item.outputBlob, name: item.outputName }] : [],
      ),
    [items],
  );

  const downloadAll = useCallback(async () => {
    await downloadZip(outputFiles);
  }, [outputFiles]);

  const convertAll = useCallback(async () => {
    if (isConverting || items.length === 0) return;
    const convertible = items.filter((item) => item.status !== "preparing");
    if (convertible.length > 0 && convertible.every((item) => item.status === "done" && item.outputBlob)) {
      await downloadAll();
      return;
    }

    setIsConverting(true);
    const converted: { blob: Blob; name: string }[] = [];
    for (const queuedItem of items) {
      if (queuedItem.status === "preparing") continue;
      setItems((current) =>
        current.map((item) => (item.id === queuedItem.id ? { ...item, status: "converting", progress: 12 } : item)),
      );
      try {
        const blob = await convertImage(
          queuedItem.file,
          queuedItem.width,
          queuedItem.height,
          queuedItem.targetFormat,
          options,
        );
        const outputName = outputNameFor(queuedItem.file.name, queuedItem.targetFormat);
        converted.push({ blob, name: outputName });
        setItems((current) =>
          current.map((item) =>
            item.id === queuedItem.id
              ? { ...item, status: "done", progress: 100, outputBlob: blob, outputName, error: undefined }
              : item,
          ),
        );
      } catch (error) {
        setItems((current) =>
          current.map((item) =>
            item.id === queuedItem.id
              ? {
                  ...item,
                  status: "error",
                  progress: 0,
                  outputBlob: undefined,
                  error: error instanceof Error ? error.message : "Conversion failed",
                }
              : item,
          ),
        );
      }
    }
    setIsConverting(false);
    if (converted.length > 0) await downloadZip(converted);
  }, [downloadAll, isConverting, items, options]);

  const readyCount = items.filter((item) => item.status !== "preparing" && item.status !== "error").length;
  const totalSourceBytes = items.reduce((total, item) => total + item.file.size, 0);
  const totalOutputBytes = outputFiles.reduce((total, item) => total + item.blob.size, 0);

  return {
    addFiles,
    clear,
    convertAll,
    downloadAll,
    groupFormat,
    isConverting,
    items,
    outputFiles,
    readyCount,
    remove,
    setGroupFormat,
    setTarget,
    totalOutputLabel: formatBytes(totalOutputBytes),
    totalSourceLabel: formatBytes(totalSourceBytes),
  };
}
