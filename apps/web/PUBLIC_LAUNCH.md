# Wemute Web — launch checklist

## 1. Domain (wemute.entropinia.com)

1. In Vercel → Project → Settings → Domains, add `wemute.entropinia.com`.
2. At the DNS provider for entropinia.com, add `CNAME wemute → cname.vercel-dns.com`.
3. Keep `wemute.vercel.app` as a redirect to the custom domain (Vercel offers this when adding the domain), so only one origin is indexed.

`vercel.json` builds with `WEMUTE_SITE_URL=https://wemute.entropinia.com`
unless the variable is set in the project. Preview deployments stay indexable
only if they share that origin, so set `WEMUTE_SITE_URL` to an empty value for
the Preview environment if you want previews noindexed.

## 2. Search and answer engines

1. Google Search Console: add the domain property, submit `/sitemap-index.xml`.
2. Bing Webmaster Tools: import from Search Console (Bing also feeds Copilot and ChatGPT search).
3. Inspect the home page and two tool pages with URL Inspection.
4. Validate structured data with the Rich Results Test and validator.schema.org.

Every page ships its own static HTML with a direct-answer paragraph, steps,
a format comparison and FAQs, plus `WebApplication`, `HowTo`, `FAQPage` and
`BreadcrumbList` JSON-LD. `robots.txt` explicitly allows GPTBot, ClaudeBot,
PerplexityBot and Google-Extended, and `/llms.txt` + `/llms-full.txt` summarise
every tool for answer engines.

## 3. Analytics

- Easiest: enable Vercel Web Analytics and set `PUBLIC_VERCEL_ANALYTICS=true` (cookieless, no banner).
- Optional GA4: set `PUBLIC_GA_MEASUREMENT_ID`; it loads only after opt-in.
- Events never include file names or contents: `files_added`, `conversion_started`, `conversion_completed`, `download_completed`, `batch_format_changed`.

## 4. AdSense

1. Set `PUBLIC_CONTACT_EMAIL` so the privacy and about pages show a real contact.
2. Apply at adsense.google.com with `wemute.entropinia.com` and verify the site.
3. In AdSense → Privacy & messaging, publish a GDPR consent message (Google-certified CMP) for EEA/UK/Switzerland.
4. Create two responsive display units ("content", "footer") and set:
   `PUBLIC_ADSENSE_ENABLED=true`, `PUBLIC_ADSENSE_CLIENT`, `PUBLIC_ADSENSE_SLOT_CONTENT`, `PUBLIC_ADSENSE_SLOT_FOOTER`, `ADSENSE_PUBLISHER_ID`.
5. Redeploy and check `/ads.txt`.

Ads only render between explanatory sections, are labelled, reserve their
height, and never appear beside the converter's drop, row, progress or
download controls.
