import type { Locale } from "./locale";

type Text = Record<Locale, string>;

export interface FormatFacts {
  id: string;
  name: string;
  kind: "image" | "video" | "audio";
  compression: Text;
  transparency?: Text;
  bestFor: Text;
  support: Text;
  note: Text;
}

const yes: Text = { en: "Yes", zh: "支持" };
const no: Text = { en: "No", zh: "不支持" };

// Facts used to build the comparison table on each conversion page.
export const FORMATS: Record<string, FormatFacts> = {
  heic: {
    id: "heic",
    name: "HEIC",
    kind: "image",
    compression: { en: "Lossy (HEVC), very efficient", zh: "有损（HEVC），压缩率很高" },
    transparency: yes,
    bestFor: { en: "Storing photos on iPhone and iPad", zh: "在 iPhone、iPad 上存储照片" },
    support: { en: "Apple devices; limited on Windows and the web", zh: "苹果设备；Windows 和网页支持有限" },
    note: {
      en: "About half the size of a JPG at similar quality, but many websites and apps still refuse it.",
      zh: "同等画质下约为 JPG 的一半大小，但很多网站和软件仍不接受。",
    },
  },
  jpg: {
    id: "jpg",
    name: "JPG",
    kind: "image",
    compression: { en: "Lossy", zh: "有损" },
    transparency: no,
    bestFor: { en: "Photos you need to share or upload anywhere", zh: "需要随处分享或上传的照片" },
    support: { en: "Universal", zh: "几乎所有设备和网站" },
    note: {
      en: "The safest choice for compatibility. Transparent areas become white.",
      zh: "兼容性最好的选择。透明区域会变成白色。",
    },
  },
  png: {
    id: "png",
    name: "PNG",
    kind: "image",
    compression: { en: "Lossless", zh: "无损" },
    transparency: yes,
    bestFor: { en: "Screenshots, logos, graphics with text", zh: "截图、Logo、带文字的图形" },
    support: { en: "Universal", zh: "几乎所有设备和网站" },
    note: {
      en: "Keeps every pixel and transparency, so photos become much larger than JPG.",
      zh: "保留每个像素和透明度，因此照片会比 JPG 大很多。",
    },
  },
  webp: {
    id: "webp",
    name: "WebP",
    kind: "image",
    compression: { en: "Lossy or lossless", zh: "有损或无损" },
    transparency: yes,
    bestFor: { en: "Images on websites", zh: "网页上的图片" },
    support: { en: "All modern browsers; some older apps lack it", zh: "所有现代浏览器；部分老软件不支持" },
    note: {
      en: "Typically 25–35% smaller than JPG at similar quality, with transparency.",
      zh: "同等画质下通常比 JPG 小 25–35%，并支持透明。",
    },
  },
  avif: {
    id: "avif",
    name: "AVIF",
    kind: "image",
    compression: { en: "Lossy (AV1), very efficient", zh: "有损（AV1），压缩率很高" },
    transparency: yes,
    bestFor: { en: "Next-generation web images", zh: "新一代网页图片" },
    support: { en: "Recent browsers; patchy in desktop apps", zh: "较新的浏览器；桌面软件支持不一" },
    note: {
      en: "Often smaller than WebP, but slower to encode and not yet accepted everywhere.",
      zh: "通常比 WebP 更小，但编码较慢，尚未被普遍接受。",
    },
  },
  gif: {
    id: "gif",
    name: "GIF",
    kind: "image",
    compression: { en: "Lossless, 256 colours", zh: "无损，最多 256 色" },
    transparency: { en: "1-bit only", zh: "仅支持全透明或不透明" },
    bestFor: { en: "Short looping animations", zh: "短小的循环动画" },
    support: { en: "Universal, autoplays everywhere", zh: "几乎所有平台，可自动播放" },
    note: {
      en: "Large files for real video; keep clips short and small for sharing.",
      zh: "用来放真实视频体积很大；分享时应尽量短、尺寸小。",
    },
  },
  mp4: {
    id: "mp4",
    name: "MP4",
    kind: "video",
    compression: { en: "Lossy (usually H.264)", zh: "有损（通常为 H.264）" },
    bestFor: { en: "Sharing and uploading video anywhere", zh: "随处分享和上传视频" },
    support: { en: "Universal", zh: "几乎所有设备和网站" },
    note: {
      en: "H.264 in MP4 plays on virtually every phone, browser, TV and editor.",
      zh: "MP4 封装的 H.264 几乎能在所有手机、浏览器、电视和剪辑软件中播放。",
    },
  },
  mov: {
    id: "mov",
    name: "MOV",
    kind: "video",
    compression: { en: "Lossy or ProRes (H.264, HEVC, ProRes)", zh: "有损或 ProRes（H.264、HEVC、ProRes）" },
    bestFor: { en: "Recording on iPhone and editing on Mac", zh: "iPhone 录制和 Mac 剪辑" },
    support: { en: "Apple devices; uneven elsewhere", zh: "苹果设备；其他平台支持不一" },
    note: {
      en: "iPhone videos are MOV with HEVC, which some Windows PCs and websites can't play.",
      zh: "iPhone 视频是 HEVC 编码的 MOV，部分 Windows 电脑和网站无法播放。",
    },
  },
  webm: {
    id: "webm",
    name: "WebM",
    kind: "video",
    compression: { en: "Lossy (VP8, VP9 or AV1)", zh: "有损（VP8、VP9 或 AV1）" },
    bestFor: { en: "Video on web pages, screen recordings", zh: "网页视频、录屏" },
    support: { en: "Browsers; limited on iPhone and editors", zh: "浏览器；iPhone 和剪辑软件支持有限" },
    note: {
      en: "Common from browser screen recorders, but many apps won't import it.",
      zh: "浏览器录屏常见格式，但很多软件无法导入。",
    },
  },
  mkv: {
    id: "mkv",
    name: "MKV",
    kind: "video",
    compression: { en: "Container for almost any codec", zh: "几乎可装任何编码的封装" },
    bestFor: { en: "Archiving video with many audio and subtitle tracks", zh: "保存带多音轨和字幕的视频" },
    support: { en: "Desktop players; poor on phones and TVs", zh: "桌面播放器；手机和电视支持较差" },
    note: {
      en: "Often the video inside is already H.264, so it can move into MP4 without re-encoding.",
      zh: "里面的视频经常已是 H.264，可以不重新编码直接换成 MP4。",
    },
  },
  mp3: {
    id: "mp3",
    name: "MP3",
    kind: "audio",
    compression: { en: "Lossy", zh: "有损" },
    bestFor: { en: "Music and voice for any player", zh: "适用于任何播放器的音乐和语音" },
    support: { en: "Universal", zh: "几乎所有设备" },
    note: {
      en: "At 192–320 kbps most listeners can't tell it from the original.",
      zh: "在 192–320 kbps 下，大多数人听不出与原始音频的区别。",
    },
  },
  wav: {
    id: "wav",
    name: "WAV",
    kind: "audio",
    compression: { en: "Uncompressed", zh: "未压缩" },
    bestFor: { en: "Editing, recording and archiving", zh: "剪辑、录音和存档" },
    support: { en: "Universal", zh: "几乎所有设备" },
    note: {
      en: "About 10 MB per stereo minute — roughly ten times a 128 kbps MP3.",
      zh: "立体声每分钟约 10 MB，大约是 128 kbps MP3 的十倍。",
    },
  },
  m4a: {
    id: "m4a",
    name: "M4A",
    kind: "audio",
    compression: { en: "Lossy (AAC) or lossless (ALAC)", zh: "有损（AAC）或无损（ALAC）" },
    bestFor: { en: "iPhone voice memos and Apple Music", zh: "iPhone 语音备忘录和 Apple Music" },
    support: { en: "Apple, most modern players", zh: "苹果设备及多数现代播放器" },
    note: {
      en: "Sounds great at small sizes, but some car stereos and web forms only take MP3.",
      zh: "体积小、音质好，但部分车载音响和网页表单只接受 MP3。",
    },
  },
  flac: {
    id: "flac",
    name: "FLAC",
    kind: "audio",
    compression: { en: "Lossless", zh: "无损" },
    bestFor: { en: "Archiving music at full quality", zh: "以完整音质保存音乐" },
    support: { en: "Most players; not every phone or car", zh: "多数播放器；并非所有手机和车载" },
    note: {
      en: "Bit-perfect but about half the size of WAV — still large for phones.",
      zh: "与原始音频完全一致，体积约为 WAV 的一半，但对手机来说仍然偏大。",
    },
  },
};

export const COMPARISON_ROWS: { key: keyof FormatFacts; label: Text }[] = [
  { key: "compression", label: { en: "Compression", zh: "压缩方式" } },
  { key: "transparency", label: { en: "Transparency", zh: "透明背景" } },
  { key: "bestFor", label: { en: "Best for", zh: "适合用于" } },
  { key: "support", label: { en: "Compatibility", zh: "兼容性" } },
];
