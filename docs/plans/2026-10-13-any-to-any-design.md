# Wemute Mac — any-to-any conversion, queue control, AI rework

Status: approved by the owner on 2026-10-13. Builds on
`2026-10-12-ice-redesign-design.md` (sentence-based UI, three states). The Mac
app comes first; the website and promotion wait until the app feels great.

## Owner feedback this answers

1. After dropping files there is no way to remove them all.
2. AI jobs stall at one percentage and then suddenly finish.
3. Remove Background and Erase results are poor, close to unusable.
4. Wemute must convert *anything to anything*: Word, Excel, PowerPoint, PDF,
   e-books, archives, data/text, fonts — not just images, video and audio.

## 1. Any-to-any

The sentence model is unchanged: one line per kind present,
「把 3 个 Word 文档 转成 [PDF ▾]」. New kinds, outputs and engines:

| Kind (sentence noun) | Inputs | Outputs | Engine |
| --- | --- | --- | --- |
| 文档 Document | DOC, DOCX, ODT, RTF, Pages, WPS | PDF, DOCX, ODT, RTF, TXT, HTML | LibreOffice (component) |
| 表格 Spreadsheet | XLS, XLSX, ODS, Numbers, CSV, TSV | XLSX, CSV, PDF, ODS, JSON | LibreOffice + Python (CSV/JSON) |
| 演示 Presentation | PPT, PPTX, ODP, Keynote | PDF, PPTX, ODP, PNG (one per slide) | LibreOffice |
| PDF | PDF | DOCX, PNG/JPG (one per page), TXT, compressed PDF, merged PDF | Python PDF libs |
| 电子书 E-book | EPUB, MOBI, AZW3, FB2 | EPUB, MOBI, AZW3, PDF | Calibre `ebook-convert` (component) |
| 压缩包 Archive | ZIP, 7Z, RAR, TAR(.GZ/.BZ2/.XZ) | extracted folder | `/usr/bin/bsdtar` (built in) + Python |
| (any batch) | any files | one ZIP / 7Z | Python |
| 数据/文本 Data & text | CSV, TSV, JSON, XLSX, MD, HTML, TXT | CSV, JSON, XLSX, MD, HTML, DOCX, TXT, PDF | Python + Pandoc (component) |
| 字体 Font | TTF, OTF, WOFF, WOFF2 | TTF, OTF, WOFF2, WOFF | fontTools |
| 矢量图 Vector | SVG | PNG, PDF | Qt `QSvgRenderer` / `QPdfWriter` |

Multi-file outcomes are sentence options, not modes:
「把 5 张图片 合成 [一个 PDF ▾]」 and 「把 3 个 PDF 合并成 [一个 PDF ▾]」;
「把 8 个文件 打包成 [ZIP ▾]」 is offered on any group through the menu entry
"打包成一个 ZIP". Outputs that produce several files (PDF → images, slides →
PNG, archive extraction) write a folder named after the source.

### Components (on-demand engines)

LibreOffice (~300 MB), Calibre (~150 MB) and Pandoc (~100 MB) are not bundled.
They are installed like the existing model packages: pinned official download
URL, exact size and SHA-256 in the bundled manifest, `.part` file, verification,
atomic activation, resumable and cancellable, removable. DMG sources are mounted
read-only with `hdiutil attach -nobrowse -readonly` and the needed app/binaries
copied out.

When a dropped kind needs a missing component, the sentence line shows an
inline row under it: 「需要先下载文档组件 · 300 MB [下载]」. Download progress
appears in that row; when it finishes the batch continues automatically if the
user had already pressed Start. Settings → 组件 lists all components (and the AI
models) with size, status and Remove.

LibreOffice runs headless with an isolated `-env:UserInstallation` profile in
Wemute's cache, one document at a time (its own lane), with a timeout and a
clear error on failure. Calibre and Pandoc run as subprocesses the same way.

### Detection

Kind is decided by extension first, then by content sniffing for ambiguous or
missing extensions (zip-based Office files vs plain ZIP, PDF magic bytes,
`file --mime-type` as fallback). Unsupported files still get the existing
"已跳过" notice, naming the file and why.

## 2. Queue control

- 「清空」 ghost button next to the primary button in the Ready state; ⌘⌫ also
  clears. After clearing, the notice line offers 「撤销」 for 8 seconds, restoring
  the exact list and choices.
- Each sentence line ends with a small × on hover that removes that whole kind
  (e.g. only the videos).
- Escape cancels an open pill menu; it never clears files.

## 3. Honest progress

Every job reports progress continuously. Engines without real progress
(LibreOffice, Calibre, AI inference) show an indeterminate shimmer on the card
plus elapsed seconds, and the overall bar advances by completed files. AI jobs
report stages ("准备模型…", "处理中…", "保存…"). First-time model preparation
(Core ML compile) is shown as its own stage, never as a frozen percentage.

## 4. AI rework

- **Remove Background**: use Apple Vision foreground instance masks
  (`VNGenerateForegroundInstanceMaskRequest`, macOS 14+) through PyObjC. Full
  resolution mask, all instances, clean alpha edges, PNG output (or HEIC with
  alpha if chosen). If no subject is found, fail with 「没有找到可以抠出的主体」.
  No download needed; remove the U²-NetP package from the catalog.
- **Erase**: inpaint only around the painted area. Compute the mask bounding box,
  expand it with context (at least 2× the box, minimum 512 px), crop at full
  resolution, inpaint the crop with LaMa, and paste back only the masked region
  with a feathered edge. Everything outside the crop is pixel-identical to the
  source. The editor gains zoom/pan, a brush-size slider with live cursor,
  undo/redo, clear, and press-and-hold to compare with the original before
  applying.
- **Upscale**: keep Real-ESRGAN, add tiled progress.
- Verify quality with real photos (people, products, pets, text overlays) and
  include before/after images in the review.

## Out of scope for now

Website changes, marketing, distribution.

## Acceptance

1. Drop a mixed folder (DOCX, XLSX, PPTX, PDF, EPUB, ZIP, CSV, MD, TTF, SVG,
   HEIC, MOV, WAV): every file joins a sentence line with sensible defaults;
   missing components are offered inline; everything converts and opens
   correctly in Preview/Pages/Numbers/Books.
2. 「清空」 and ⌘⌫ clear the list; 「撤销」 restores it; per-line × works.
3. No progress indicator freezes for more than one second without visible
   activity.
4. Remove Background output on real photos has crisp, full-resolution edges;
   Erase leaves the rest of the photo untouched and blends the erased area.
5. `uv run pytest` and the QML smoke test pass; new engines have tests with real
   fixture files.
