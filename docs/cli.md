# Wemute command line

Wemute runs without a window from the command line. Use it to:

- turn any file into text that a language model can read (`extract`);
- convert files with the same tools as the app (`convert`).

Everything runs on this Mac.

## Install

In Wemute, open **Settings › Integrations › Command line** and choose **Install**.
This adds a `wemute` command to `/opt/homebrew/bin`, or to `~/.local/bin` if
that folder isn't writable.

You can also call the binary directly:

```sh
/Applications/Wemute.app/Contents/MacOS/Wemute --cli <command> …
```

`wemute --version` prints the version. `wemute --help` and
`wemute <command> --help` list the options.

## `wemute extract` — any file as text for a language model

```sh
wemute extract report.pdf                       # Markdown on stdout
wemute extract call.m4a --speakers              # who said what, with timestamps
wemute extract inbox/ --format json             # one JSON line per file
wemute extract deck.pptx notes.docx --out ~/digest   # one .md file per input
```

| Option | Meaning |
|---|---|
| `--format md` (default) | Markdown that keeps structure: headings, lists, tables, pages, slides, speakers. |
| `--format txt` | The same content without Markdown markup. |
| `--format json` | One JSON object per line, one line per document (see below). |
| `--out DIR` | Write one file per input into `DIR` and print one result line per input. |
| `--ocr auto\|always\|never` | `auto` reads with OCR only the PDF pages and images that have no text layer. |
| `--speakers` | Recordings: label each speaker (`S01`, `S02`, …). Uses MOSS-Transcribe-Diarize in ThunderTalk. |
| `--language auto\|zh\|en\|…` | The speech language of recordings. |
| `--max-rows N` | The most rows kept per sheet or table (default 5000); a note says when rows were cut. |

### What each file type gives

| Input | Output |
|---|---|
| PDF | `## Page N` sections. Tables become Markdown tables. Scanned pages are read with Apple Vision OCR and counted in `meta.ocr_pages`. |
| Word `.docx` | Headings, bullet lists and tables, in document order. |
| `.doc`, `.rtf`, `.odt`, `.webarchive` | Read through macOS `textutil`: headings, paragraphs and tables. |
| Excel `.xlsx` | A `## Sheet` section per sheet, each holding a table of computed values. |
| PowerPoint `.pptx` | A `## Slide N: Title` section per slide, with bullets, tables and speaker notes. |
| Pages, Numbers, Keynote, `.xls`, `.ppt`, `.ods`, `.odp` | Converted with the LibreOffice component, then read as above. |
| Images (JPG, PNG, HEIC, WebP, TIFF…) | OCR text in reading order, plus QR codes and barcodes. `meta` has the size and the date the photo was taken. |
| Audio and video | A transcript from ThunderTalk's most accurate downloaded model, with a timestamp about every 30 s. With `--speakers`, one paragraph per turn. |
| HTML | Markdown. Scripts, styles and navigation are dropped. |
| E-mail `.eml` | The headers, the body, and every attachment as its own document. |
| EPUB | Chapters in reading order. MOBI and AZW3 go through the Calibre component; DRM-protected books can't be read. |
| ZIP, 7Z, TAR, RAR | Every file inside is a document of its own. |
| A folder | Every file in it, recursively. Hidden files are skipped. |
| CSV, TSV, JSON records | A table. Nested JSON is kept as pretty-printed JSON. |
| SVG | Title, description and every text label. |
| Text and code | As is; code goes in a fenced block. |

### JSON lines

With `--format json`, stdout carries nothing but JSON, one object per line:

```json
{"type": "document", "source": "/path/report.pdf", "kind": "pdf", "title": "…",
 "markdown": "## Page 1\n\n…", "text": "…",
 "meta": {"pages": 12, "ocr_pages": 2, "tables": 3},
 "warnings": ["2 scanned page(s) read with OCR"]}
{"type": "error", "source": "/path/x.bin", "code": "unsupported", "error": "…"}
```

- Archive members and e-mail attachments come after their container, one line
  each. Their `source` reads `pack.zip › folder/file.xlsx`.
- `kind` is one of: `pdf`, `document`, `spreadsheet`, `slides`, `image`,
  `recording`, `web page`, `email`, `ebook`, `archive`, `folder`, `table`,
  `data`, `text`, `vector`. A member that couldn't be read is `skipped`, with
  the reason in `warnings`.

### Exit status and errors

- The exit status is `0` when every input was read and `1` when any failed.
  Inputs that fail never stop the others.
- The error `code` is one of:
  - `not_found`
  - `unsupported`
  - `unreadable`
  - `encrypted`
  - `component_missing` (install it in Settings › Components)
  - `thundertalk_missing`
  - `thundertalk_outdated`
  - `no_speech`
  - `no_model`
  - `failed`
- In Markdown and text mode, errors go to stderr. With `--format json` or
  `--out`, errors go to stdout as JSON.
- Log messages from libraries always go to stderr, never to stdout.

## `wemute convert` — the app's tools, headless

```sh
wemute convert photo.heic                          # each kind to its default format (Settings › Convert)
wemute convert --action to_pdf *.docx              # one tool for every file it applies to
wemute convert --action remove_background a.jpg --plain   # print only the output paths
wemute actions                                     # every tool id and its title
```

- Outputs follow the app's settings: the save location and the "-wemute"
  filename suffix.
- Files the chosen tool doesn't apply to are skipped, never converted to a
  default format.
- stdout carries one JSON line per file, then a result line:

  ```json
  {"type": "file", "source": "…", "ok": true, "output": "…", "error": ""}
  {"type": "result", "ok": true, "converted": 3, "failed": 0}
  ```

- `--notify` also shows a macOS notification when the run finishes.

## Requirements

- macOS 14 or later on Apple Silicon.
- Recordings need ThunderTalk with its command line (ThunderTalk CLI version 2
  for `--speakers` and the most-accurate-model choice).
- Pages, Numbers, Keynote and old Office files need the LibreOffice component.
- MOBI and AZW3 need the Calibre component.
