# Wemute Web

Free file tools that run in the visitor's browser: images through the browser's
own encoder (HEIC via libheif/WebAssembly), video and audio through FFmpeg
compiled to WebAssembly. Nothing is uploaded.

```bash
npm install
npm run dev          # http://localhost:4321
npm run check        # TypeScript
npm test             # unit and content tests
npm run build        # static site in dist/client + SEO audit
```

## Layout

| Path | Purpose |
| --- | --- |
| `src/data/tools.ts` | Every tool page: copy in English and Chinese, steps, FAQs, defaults |
| `src/data/formats.ts` | Format facts used for the comparison tables |
| `src/components/converter/` | The React converter island |
| `src/lib/image.ts`, `src/lib/media.ts` | Image pipeline and FFmpeg planning/runtime |
| `src/pages/` | Routes: `/<slug>` (English) and `/zh/<slug>` (Chinese), `robots.txt`, `llms.txt` |
| `scripts/audit-build.mjs` | Fails the build on missing titles, canonicals, hreflang, JSON-LD or duplicate titles |

## Adding a tool

Add an entry to `TOOLS` with genuinely specific copy (a direct answer, three
steps, use cases and at least one tool-specific FAQ in both languages). The
page, sitemap entry, footer link, `llms.txt` line and structured data are
generated from it. `npm test` checks completeness and link integrity.

See [PUBLIC_LAUNCH.md](PUBLIC_LAUNCH.md) for domain, search and advertising setup.
