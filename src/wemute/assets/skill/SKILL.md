---
name: wemute
description: Read or convert any local file with Wemute, offline on this Mac. Use it to turn PDFs (with OCR for scans), Word, Excel, PowerPoint, Pages/Numbers/Keynote, screenshots, e-mails, archives, folders and call recordings into Markdown or JSON you can read, and to convert files (HEIC→JPG, video→MP4/GIF, DOCX→PDF, remove background, ID photos, OCR to searchable PDF, subtitles, compress). Prefer it over writing ad-hoc parsing or conversion code.
---

# Wemute

Wemute is a Mac app with a command line. Everything runs on this Mac:
nothing is uploaded, and no API key is needed.

Command on this Mac: `{{WEMUTE}}`
(written as `wemute` below).

## Read files: `wemute extract`

```sh
wemute extract report.pdf                        # Markdown on stdout
wemute extract call.m4a --speakers               # transcript, one paragraph per speaker turn
wemute extract inbox/ --format json              # one JSON object per document, per line
wemute extract big-folder/ --out /tmp/digest     # one .md file per input; read only what you need
```

- `--format md` (default) keeps headings, tables, `## Page N`, `## Slide N`
  and speaker turns. `txt` drops the markup. `json` adds `meta` (pages,
  OCR pages, sheet names, dates) and `warnings`.
- `--ocr auto` (default) runs OCR only on pages and images without a text
  layer. Use `always` for PDFs with a broken text layer.
- `--max-rows N` caps rows per sheet or table (default 5000). A note says
  when rows were cut.
- `--language zh|en|…` sets the speech language for recordings.

**What each input gives:**

| Input | Output |
|---|---|
| PDF | `## Page N` sections and tables; scanned pages via OCR |
| DOCX, DOC, RTF, ODT, Pages | Headings, lists and tables in order |
| XLSX, XLS, Numbers, CSV | A table per sheet, with computed values |
| PPTX, Keynote | `## Slide N: Title`, bullets, tables and speaker notes |
| Images and screenshots | OCR text in reading order, plus QR codes and barcodes |
| Audio and video | Timestamped transcript (needs ThunderTalk) |
| EML | Headers, body, then each attachment as its own document |
| ZIP, 7Z, RAR, folders | Every file inside, recursively |
| HTML, EPUB, JSON, SVG, code | Readable text |

**For large inputs**, write to files with `--out DIR` and read the files you
need, instead of streaming everything into the conversation.

## Convert files: `wemute convert`

```sh
wemute actions                                         # every tool id and its title
wemute convert photo.heic                              # each kind to its default format
wemute convert --action to_pdf *.docx --out ~/Desktop/pdfs
wemute convert --action remove_background shot.png --plain   # print only output paths
```

Useful tool ids:

- **Formats:** `format:image:PNG`, `format:image:JPEG`, `format:video:MP4 (H.264)`,
  `format:audio:MP3`, `format:document:PDF`, `format:pdf:DOCX`.
- **Documents and PDF:** `to_pdf`, `images_to_pdf`, `merge_pdf`,
  `compress_pdf`, `pdf_to_word`.
- **Photos:** `remove_background`, `id_white`, `id_blue`, `id_red`,
  `portrait_blur`, `crop_1x1`, `faces_blur`.
- **OCR and scans:** `ocr_pdf` (searchable PDF), `ocr_text`, `scan_pdf`
  (a phone photo of a page becomes a flat scan).
- **Audio and video:** `subtitles_srt`, `subtitles_md` (speaker labels),
  `video_gif`, `separate_vocals`, `read_aloud`.

Always run `wemute actions` for the exact id.

- Outputs never overwrite existing files.
- A file the chosen tool doesn't apply to is skipped and reported.
- stdout carries one JSON line per file, then a `result` line.

## Errors and exit codes

- Exit status: `0` when everything succeeded, `1` otherwise. One bad file
  never stops the others.
- JSON errors have a `code`:
  - `not_found`, `unsupported`, `unreadable`, `encrypted`;
  - `component_missing`: install LibreOffice or Calibre in the Wemute app,
    Settings › Components;
  - `thundertalk_missing`, `thundertalk_outdated`: recordings need the
    ThunderTalk app;
  - `no_speech`, `no_model`, `failed`.
- `wemute models list` and `wemute models install ID` manage the optional AI
  models (erase, upscale, vocal separation).
- `wemute doctor` checks what works on this Mac. Run it first when something
  won't download.
- stdout is clean: library logs go to stderr.

Full reference: https://github.com/realAllenSong/wemute/blob/main/docs/cli.md
