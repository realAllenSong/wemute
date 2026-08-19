# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Durable product direction

- The public website must teach the product before dropping visitors into the queue: use a concise discovery homepage and focused image-tool routes, then reveal the existing batch workspace after files are added.
- Keep the established graphite, blue-accented, restrained Wemute visual system. Borrow iLoveIMG's clarity and discoverability, not its dense tool-card wall.
- The core workflow stays local-first and immediate: one large drop action, group-level defaults, optional per-file overrides, and no account requirement.
- Advertising must never sit beside upload, conversion, file-row, progress, or download controls. Reserve stable placements only after useful explanatory content and hide ads from active processing/result views.
