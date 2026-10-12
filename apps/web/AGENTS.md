# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Durable product direction

- Stack: Astro static pages (one crawlable HTML file per route, English at `/<slug>`, Chinese at `/zh/<slug>`) with the converter as a React island in `src/components/converter/`. Tool content lives in `src/data/tools.ts`; format facts in `src/data/formats.ts`.
- Visual system: "Porcelain & Cobalt", shared with the Mac app — porcelain surfaces, graphite text, one cobalt "seam" accent that means transformation (progress, primary action, focus), following the system light/dark appearance. The owner's ThunderTalk app is the bar for taste and polish, but Wemute must not copy its palette, serif type or sidebar structure.
- The core workflow stays local-first and immediate: one large drop action, group-level defaults, optional per-file overrides, no account. Image and audio tool pages convert on drop; video tools wait for the user to set options.
- Advertising must never sit beside upload, conversion, file-row, progress, or download controls. Ads appear only between explanatory sections, are labelled, and reserve their height.
- The desktop app is a private tool for the owner. Do not advertise, distribute, or link to it from the public website.
- The public website is a free, browser-local utility funded by clearly separated advertising. Search and answer-engine visibility must come from useful, independently valuable tool pages (direct answer, steps, format comparison, specific FAQs), never thin keyword permutations.
