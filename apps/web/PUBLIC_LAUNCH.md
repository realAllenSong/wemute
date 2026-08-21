# Wemute Web public launch

## Product boundary

Wemute Web is the public product. It is free, requires no account, and processes supported image contents and filenames locally in the browser. The desktop app is private and is not promoted by the website.

Revenue comes from clearly labeled advertising placed after useful content. Ads never appear beside upload, conversion, file rows, progress, or download controls, and disappear entirely from the active workspace.

## 1. Production domain

Choose one canonical HTTPS origin and build with both variables set to the same value:

```bash
WEMUTE_SITE_URL=https://your-domain.example \
VITE_SITE_URL=https://your-domain.example \
npm run build
```

The build fails for a non-HTTPS public origin. Without a domain, it deliberately creates a `noindex` preview instead of guessing a canonical URL.

After deployment, verify all eight routes return their own HTML, title, description, canonical URL, visible H1, and JSON-LD before submitting the sitemap.

## 2. Search and answer-engine discovery

The current pages use one page per genuinely different job. Each page contains:

- a direct explanation of what the tool does;
- a working browser-local tool;
- a three-step method;
- distinct use cases and factual FAQ answers;
- links to related tools;
- `WebApplication` structured data and, on tool pages, `BreadcrumbList`;
- unique static metadata and crawlable HTML before JavaScript runs.

Do not generate hundreds of format permutations until each route can enforce its claimed source and output formats and provide independent value. Thin `[format]-to-[format]` pages are intentionally excluded.

Launch tasks owned by the site operator:

1. Verify the production domain in Google Search Console and Bing Webmaster Tools.
2. Submit `/sitemap.xml` in both tools.
3. Inspect the homepage and two representative tool URLs with URL Inspection / live tests.
4. Validate JSON-LD with Google's Rich Results Test and Schema.org Validator.
5. Monitor indexed pages, search queries, Core Web Vitals, and Bing AI citations after launch.

`llms.txt` provides a compact factual map for systems that choose to read it. It does not replace crawlable pages, sitemaps, structured data, or useful content.

## 3. Privacy-first analytics

Set `VITE_GA_MEASUREMENT_ID` only if GA4 is wanted. The Google tag is not loaded until a visitor explicitly opts in. Declining analytics does not disable any tool.

The event contract is deliberately small:

| Event | Purpose | Properties |
| --- | --- | --- |
| `page_viewed` | Compare discovery and tool routes | `page_path`, `page_title` |
| `files_added` | Measure activation | `file_count`, `file_category` |
| `batch_format_changed` | Learn preferred outputs | `output_format` |
| `conversion_started` | Measure intent | `file_count`, `output_format` |
| `conversion_completed` | Measure reliability | attempted, succeeded, failed counts |
| `download_completed` | Measure completed value | `file_count`, `download_type` |

Never add filenames, paths, image contents, raw dimensions tied to a file, or other personal data to analytics events.

## 4. Advertising

Advertising stays off until every required value is real:

```bash
VITE_ADSENSE_CLIENT=ca-pub-1234567890123456
VITE_ADSENSE_HOME_SLOT=1234567890
VITE_ADSENSE_TOOL_SLOT=2345678901
ADSENSE_PUBLISHER_ID=pub-1234567890123456
VITE_ADSENSE_CONSENT_READY=true
```

The final flag means a Google-certified CMP has been configured and tested for the production site. It is a deliberate release gate, not a substitute for CMP configuration. Do not turn it on merely to make an ad appear.

With a valid publisher ID, the build generates the matching root `ads.txt` line and the AdSense account meta tag. With missing or placeholder values, it generates neither and loads no advertising script.

Before public ad serving:

1. Add and approve the production domain in AdSense.
2. Configure a Google-certified CMP for applicable EEA, UK, and Switzerland traffic.
3. Create separate responsive home and tool-content slots.
4. Confirm ads appear only after useful content and never in the converter workspace.
5. Check `/ads.txt` returns HTTP 200 and exactly matches the AdSense publisher ID.
6. Test mobile layout shift and accidental-click distance.

## 5. Release gate

- Typecheck, unit tests, production build audit, and Sites worker tests pass.
- Mobile width has no horizontal overflow.
- No third-party scripts load when analytics and ads are unconfigured.
- Privacy, terms, and about pages use final contact and operator details.
- Production robots allow crawling and reference the canonical sitemap.
- Preview/staging deployments remain `noindex`.
- Search Console, Bing Webmaster Tools, AdSense, CMP, and optional GA4 use the production origin only.
