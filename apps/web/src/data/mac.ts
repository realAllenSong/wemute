// Every release also carries an unversioned Wemute.dmg, so this always downloads the latest.
export const MAC_DOWNLOAD_URL = "https://github.com/realAllenSong/wemute/releases/latest/download/Wemute.dmg";
export const MAC_RELEASES_URL = "https://github.com/realAllenSong/wemute/releases/latest";

// The Mac app and its command line, described for answer engines (llms.txt).
export const MAC_APP_LINES = [
  "## Wemute for Mac (desktop app and command line)",
  "",
  "Wemute is also a free, open-source (AGPL-3.0) Mac app for macOS 14+ on Apple Silicon, signed and notarized by Apple: https://github.com/realAllenSong/wemute (direct download: https://github.com/realAllenSong/wemute/releases/latest/download/Wemute.dmg). Everything runs on the Mac; nothing is uploaded.",
  "",
  "- Converts images (HEIC, RAW, JPG, PNG, WebP, AVIF), video (MOV, MP4, MKV, WebM), audio, Word, Excel, PowerPoint, Pages, Numbers, Keynote, PDF (to Word, images, text, searchable PDF), e-books (EPUB, MOBI, AZW3), archives, fonts and data files.",
  "- Photo and scan tools on Apple's Vision framework: remove background, ID photo backdrops (white, blue, red), portrait blur, OCR in Chinese and English, scan and flatten a phone photo of a page, smart crop, face blur, straighten, QR codes, blurry and duplicate photos.",
  "- Subtitles (SRT, VTT, transcripts, speaker labels) and read-aloud, through ThunderTalk.",
  "- Finder Quick Actions, a Shortcuts action, ⌘K tool search.",
  "- Command line for scripts and AI agents: `wemute extract FILE_OR_FOLDER` turns any file into Markdown, text or JSON lines a language model can read (PDF pages and tables with OCR for scanned pages, Word, Excel, PowerPoint with notes, screenshots, call recordings with speaker labels, e-mails with attachments, archives). `wemute convert --action ID FILES` runs any tool without the window. Reference: https://github.com/realAllenSong/wemute/blob/main/docs/cli.md",
  "- Open-source alternative to Permute, CloudConvert, Convertio and iLovePDF.",
  "",
];
