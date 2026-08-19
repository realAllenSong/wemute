# Wemute Web product strategy

## W1 implementation status

W1 is now implemented in `apps/web` as a responsive React/TypeScript workspace.
It performs PNG, JPEG and WebP conversion in Canvas, applies resize, quality and
rounded corners, preserves the desktop app's group-level output plus per-file
override model, and downloads a collision-safe batch ZIP. English and Simplified
Chinese follow the browser locale and can be switched in place.

The production build and static-hosting worker are ready, but deployment and ads
are intentionally not enabled. The workspace remains ad-free, account-free and
upload-free. Browser HEIC decoding and metadata retention remain capability
limits rather than claims Wemute hides.

## Product decision

Build the web edition, but do not make it a server-hosted clone of the desktop app.

The web product should keep the same promise—drop files, choose one outcome, process—but use a browser-first capability matrix:

- Run common image work entirely in the browser: JPEG, PNG, WebP and AVIF conversion, resize, quality compression, crop, rotate and rounded corners.
- Add background removal and image upscaling as downloadable browser model packs only after measuring memory use on ordinary laptops and phones.
- Offer small audio/video conversions through a worker-based WebAssembly runtime with a clear file-size ceiling. Keep large media, HEVC/ProRes, batch automation and long-running AI work as reasons to download the desktop app.
- Never silently upload a file. If a future server fallback is introduced, make that a separate, explicit action with deletion timing shown before upload.

This split avoids browser pretending to be a workstation. WebCodecs exposes browser codecs but deliberately does not require any implementation to support a particular codec. FFmpeg.wasm keeps files in the browser and runs work off the main thread, but its own performance documentation says it is slower than native FFmpeg. Sources: [W3C WebCodecs](https://www.w3.org/TR/webcodecs/), [ffmpeg.wasm overview](https://ffmpegwasm.netlify.app/docs/overview/), [ffmpeg.wasm performance](https://ffmpegwasm.netlify.app/docs/performance/).

## Monetization reality

There are two different Google/Meta products in the idea:

- **Google AdSense** is publisher revenue: Wemute shows ads and may earn money.
- **Google Ads and Meta Ads** are user-acquisition channels: Wemute pays to reach users. They are costs, not revenue.

The free web edition can test AdSense, but the conversion canvas must never become an ad trap. Google explicitly disallows ads that interfere with controls and warns against ads on screens with little or no publisher content. AdSense eligibility also calls for original, useful content. Therefore:

- Keep the actual workspace ad-free while a conversion is running.
- Reserve at most one stable ad slot on explanatory landing/result pages, away from Drop, Download and Convert controls.
- Publish genuinely useful format guides, privacy explanations and comparison pages; do not manufacture thin doorway pages around every extension pair.
- Do not ask users to click ads or style ads like Wemute buttons.
- Add consent, privacy, cookie and regional compliance before personalized advertising.

Sources: [Google Publisher Policies](https://support.google.com/adsense/answer/10502938), [AdSense Program Policies](https://support.google.com/adsense/answer/48182), [AdSense eligibility](https://support.google.com/adsense/answer/9724), [Meta advertising](https://www.facebook.com/business/ads/instagram-ad).

## Recommended business model

1. **Free web:** fast local image tools, sensible limits, no account, one restrained ad placement on content pages.
2. **Free desktop Alpha:** full local media conversion and image tooling, no ads.
3. **Wemute Pro:** one-time desktop purchase for unrestricted batch workflows, watcher folders, presets, PDF tools and AI model packs.
4. **Acquisition later:** spend on Google/Meta only after organic users demonstrate that activation and repeat use can recover the acquisition cost.

Advertising should be supplemental revenue, not the product's reason to exist. A clean desktop upgrade is likely to be more aligned with Wemute's premium positioning than maximizing page views.

## Technical shape

Use a monorepo when web implementation begins:

```text
apps/
  desktop/       PySide6/QML shell and native engines
  web/           TypeScript UI, service workers and Web Workers
packages/
  capability-spec/  versioned JSON schemas, formats, presets and copy
  test-vectors/     small shared media fixtures and expected metadata
```

Share the capability manifest, presets, copy and test vectors. Do not force Python conversion code into the browser or duplicate native FFmpeg behavior in JavaScript.

Web runtime order:

1. Browser-native image APIs and small WASM codecs.
2. WebCodecs when the requested codec is actually reported as supported.
3. A trimmed FFmpeg.wasm core in a dedicated worker for bounded jobs.
4. “Open in Wemute” deep link for unsupported, large or memory-intensive work.

## Web V1 release gates

- A 20-image batch remains interactive and survives one corrupt file.
- No file bytes leave the browser in local mode; this is verified in an automated network test.
- Worker cancellation releases memory and does not leave object URLs behind.
- Mobile memory limits and unsupported formats fail before work starts with a useful desktop handoff.
- Core Web Vitals remain healthy before loading any codec/model bundle; engines load only after user intent.
- Ads never move the Drop, Convert or Download controls and never appear during processing.
- Privacy policy, terms, copyright reporting path and consent behavior are complete before AdSense review.

## Suggested sequence

- W1: image-only web workspace and capability detection. **Implemented.**
- W2: SEO/content shell, privacy pages, analytics without file metadata, and restrained AdSense experiment.
- W3: small audio/video worker beta with explicit limits.
- W4: desktop deep links, Pro purchase path and optional AI packs.
