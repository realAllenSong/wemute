# Wemute Web

The public Wemute product: free, browser-local image tools designed for organic discovery and clearly separated advertising.

## Included

- Drag, drop, or choose multiple images.
- Set PNG, JPEG, or WebP once for the full queue, then override individual files.
- Resize, quality, and rounded-corner controls.
- Local Canvas conversion and batch ZIP download. Files are never uploaded.
- English and Simplified Chinese interface.
- Dedicated crawlable pages for conversion, compression, resizing, and rounded corners.
- Route-specific metadata, canonical URLs, JSON-LD, static fallback content, and internal links.
- Privacy, terms, and about pages.
- Optional consent-gated GA4 events and optional AdSense slots. Both are disabled by default.

## Public routes

- `/`
- `/tools/convert-image`
- `/tools/compress-image`
- `/tools/resize-image`
- `/tools/round-corners`
- `/about`
- `/privacy`
- `/terms`

## Development

```bash
npm install
npm run dev
```

Verification:

```bash
npm run typecheck
npm test
npm run build
npm run test:sites
```

## Safe preview and production builds

`npm run build` without a production origin creates a safe preview: every page is `noindex`, `robots.txt` disallows crawling, and no sitemap is published.

An indexable production build requires a verified HTTPS origin:

```bash
WEMUTE_SITE_URL=https://example.com \
VITE_SITE_URL=https://example.com \
npm run build
```

That build produces unique static HTML for every public route plus `sitemap.xml`, `robots.txt`, and `llms.txt`. `llms.txt` is an experimental plain-text site summary, not a search ranking mechanism.

See [PUBLIC_LAUNCH.md](./PUBLIC_LAUNCH.md) for domain, Search Console, analytics, consent, and advertising setup.
