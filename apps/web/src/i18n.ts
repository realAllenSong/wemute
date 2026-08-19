import type { Locale } from "./types";

const translations = {
  en: {
    addFiles: "Add Files",
    allTo: "All →",
    browserNote: "Converted in your browser. Nothing is uploaded.",
    chooseFiles: "Choose images",
    clearAll: "Clear All",
    completed: "Completed",
    converting: "Converting…",
    convertAll: "Convert All",
    cornerRadius: "Rounded corners",
    downloadAll: "Download All",
    dropHere: "Drop images here",
    error: "Couldn’t convert",
    files: "Files",
    imageSupport: "PNG, JPEG and WebP · stays on this device",
    images: "Images",
    options: "Options",
    original: "Original",
    preparing: "Reading image…",
    quality: "Quality",
    qualityBalanced: "Balanced",
    qualityHigh: "High Quality",
    qualitySmall: "Small File",
    ready: "Ready",
    readyHint: "Waiting to convert",
    remove: "Remove",
    resize: "Resize",
    resizeCustom: "Custom width",
    resizeHalf: "50%",
    resizeLong: "Long edge 1920 px",
    retry: "Retry",
    webLocal: "Local web workspace",
  },
  zh: {
    addFiles: "添加文件",
    allTo: "全部转为",
    browserNote: "所有处理都在浏览器本地完成，不会上传。",
    chooseFiles: "选择图片",
    clearAll: "清空",
    completed: "已完成",
    converting: "转换中…",
    convertAll: "全部转换",
    cornerRadius: "圆角",
    downloadAll: "全部下载",
    dropHere: "拖入图片",
    error: "转换失败",
    files: "个文件",
    imageSupport: "PNG、JPEG、WebP · 仅在本机处理",
    images: "图片",
    options: "选项",
    original: "原始尺寸",
    preparing: "正在读取…",
    quality: "质量",
    qualityBalanced: "均衡",
    qualityHigh: "高质量",
    qualitySmall: "更小文件",
    ready: "就绪",
    readyHint: "等待转换",
    remove: "移除",
    resize: "缩放",
    resizeCustom: "自定义宽度",
    resizeHalf: "50%",
    resizeLong: "最长边 1920 px",
    retry: "重试",
    webLocal: "本地网页工作台",
  },
} as const;

export type TranslationKey = keyof (typeof translations)["en"];

export function t(locale: Locale, key: TranslationKey): string {
  return translations[locale][key];
}

export function defaultLocale(language = navigator.language): Locale {
  return language.toLocaleLowerCase().startsWith("zh") ? "zh" : "en";
}
