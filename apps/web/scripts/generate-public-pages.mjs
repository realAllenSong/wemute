#!/usr/bin/env node
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  INDEXABLE_PATHS,
  SITE_CONTENT,
  TOOL_CONTENT,
  contentForPath,
  metadataForPath,
  structuredDataForPath,
} from "../src/site-content.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const client = path.join(root, "dist", "client");
const baseHtml = readFileSync(path.join(client, "index.html"), "utf8");

function resolveSite() {
  const value = process.env.WEMUTE_SITE_URL?.trim();
  if (!value) return { origin: "https://wemute.invalid", indexable: false };
  const url = new URL(value);
  const local = ["localhost", "127.0.0.1"].includes(url.hostname);
  if (url.protocol !== "https:" && !(local && url.protocol === "http:")) {
    throw new Error("WEMUTE_SITE_URL must use HTTPS (HTTP is allowed only for localhost)");
  }
  return { origin: url.origin, indexable: !local };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function link(pathname, label) {
  return `<a href="${escapeHtml(pathname)}">${escapeHtml(label)}</a>`;
}

function staticShell(content) {
  const brand = `<header class="static-shell__header">${link("/", "Wemute")}<nav>${TOOL_CONTENT.map((tool) => link(tool.path, tool.shortTitle.en)).join("")}</nav></header>`;
  const footer = `<footer class="static-shell__footer">${link("/about", "About")}${link("/privacy", "Privacy")}${link("/terms", "Terms")}</footer>`;

  if (content.kind === "home") {
    return `<main class="static-shell">${brand}<article><h1>${escapeHtml(content.h1.en)}</h1><p>${escapeHtml(content.intro.en)}</p><p>Wemute processes supported images locally in your browser. Image contents and filenames are not uploaded to Wemute.</p><section><h2>Free browser-local image tools</h2><ul>${TOOL_CONTENT.map((tool) => `<li>${link(tool.path, tool.shortTitle.en)} — ${escapeHtml(tool.description.en)}</li>`).join("")}</ul></section><section><h2>Good to know</h2>${content.faqs.map((faq) => `<details><summary>${escapeHtml(faq.question.en)}</summary><p>${escapeHtml(faq.answer.en)}</p></details>`).join("")}</section></article>${footer}</main>`;
  }

  if (content.kind === "tool") {
    return `<main class="static-shell">${brand}<article><p>${link("/", "All image tools")}</p><h1>${escapeHtml(content.title.en)}</h1><p>${escapeHtml(content.description.en)}</p><section><h2>How ${escapeHtml(content.shortTitle.en.toLowerCase())} works</h2><p>${escapeHtml(content.answer.en)}</p><ol>${content.steps.map((step) => `<li>${escapeHtml(step.en)}</li>`).join("")}</ol></section><section><h2>Common uses</h2><ul>${content.useCases.map((item) => `<li>${escapeHtml(item.en)}</li>`).join("")}</ul></section><section><h2>Questions about this tool</h2>${content.faqs.map((faq) => `<details><summary>${escapeHtml(faq.question.en)}</summary><p>${escapeHtml(faq.answer.en)}</p></details>`).join("")}</section><p>Enable JavaScript to process images locally in this browser.</p></article>${footer}</main>`;
  }

  return `<main class="static-shell">${brand}<article><h1>${escapeHtml(content.title.en)}</h1><p>${escapeHtml(content.intro.en)}</p><p><small>Updated ${escapeHtml(content.updated)}</small></p>${content.sections.map((section) => `<section><h2>${escapeHtml(section.heading.en)}</h2><p>${escapeHtml(section.body.en)}</p></section>`).join("")}</article>${footer}</main>`;
}

function headFor(content, site) {
  const metadata = metadataForPath(content.path);
  const canonical = new URL(metadata.path, site.origin).toString();
  const schema = JSON.stringify(structuredDataForPath(content.path, site.origin)).replaceAll("<", "\\u003c");
  const robots = site.indexable ? "index, follow, max-image-preview:large" : "noindex, nofollow";
  const adsenseClient = process.env.VITE_ADSENSE_CLIENT?.trim();
  return [
    `<meta name="description" content="${escapeHtml(metadata.description)}" />`,
    `<meta name="robots" content="${robots}" />`,
    `<link rel="canonical" href="${escapeHtml(canonical)}" />`,
    `<link rel="icon" href="/wemute-icon-256.png" type="image/png" />`,
    `<link rel="apple-touch-icon" href="/wemute-icon-256.png" />`,
    `<meta property="og:type" content="website" />`,
    `<meta property="og:site_name" content="Wemute" />`,
    `<meta property="og:title" content="${escapeHtml(metadata.title)}" />`,
    `<meta property="og:description" content="${escapeHtml(metadata.description)}" />`,
    `<meta property="og:url" content="${escapeHtml(canonical)}" />`,
    `<meta property="og:image" content="${escapeHtml(new URL("/wemute-icon-256.png", site.origin).toString())}" />`,
    `<meta property="og:image:alt" content="Wemute app icon" />`,
    `<meta name="twitter:card" content="summary" />`,
    `<meta name="twitter:title" content="${escapeHtml(metadata.title)}" />`,
    `<meta name="twitter:description" content="${escapeHtml(metadata.description)}" />`,
    `<meta name="twitter:image" content="${escapeHtml(new URL("/wemute-icon-256.png", site.origin).toString())}" />`,
    /^ca-pub-\d+$/.test(adsenseClient ?? "") ? `<meta name="google-adsense-account" content="${adsenseClient}" />` : "",
    `<script id="wemute-structured-data" type="application/ld+json">${schema}</script>`,
  ].filter(Boolean).join("\n    ");
}

function renderPage(content, site) {
  const metadata = metadataForPath(content.path);
  return baseHtml
    .replace(/<meta name="description"[^>]*>\s*/i, "")
    .replace(/<title>[^<]*<\/title>/i, `<title>${escapeHtml(metadata.title)}</title>\n    ${headFor(content, site)}`)
    .replace('<div id="root"></div>', `<div id="root">${staticShell(content)}</div>`);
}

function outputPath(pathname) {
  return pathname === "/"
    ? path.join(client, "index.html")
    : path.join(client, pathname.slice(1), "index.html");
}

const site = resolveSite();
for (const pathname of INDEXABLE_PATHS) {
  const content = contentForPath(pathname);
  const destination = outputPath(pathname);
  mkdirSync(path.dirname(destination), { recursive: true });
  writeFileSync(destination, renderPage(content, site));
}

const robots = site.indexable
  ? `User-agent: *\nAllow: /\n\nSitemap: ${new URL("/sitemap.xml", site.origin)}\n`
  : "User-agent: *\nDisallow: /\n";
writeFileSync(path.join(client, "robots.txt"), robots);

const sitemapPath = path.join(client, "sitemap.xml");
if (site.indexable) {
  const urls = INDEXABLE_PATHS.map((pathname) => `  <url><loc>${new URL(pathname, site.origin)}</loc><lastmod>2026-08-21</lastmod></url>`).join("\n");
  writeFileSync(sitemapPath, `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`);
} else {
  rmSync(sitemapPath, { force: true });
}

const publicBase = site.indexable ? site.origin : "[production origin]";
writeFileSync(path.join(client, "llms.txt"), [
  "# Wemute",
  "",
  SITE_CONTENT.tagline.en + ".",
  "Supported image work happens locally in the visitor's browser; image contents and filenames are not uploaded to Wemute.",
  "",
  "## Tools",
  ...TOOL_CONTENT.map((tool) => `- [${tool.shortTitle.en}](${publicBase}${tool.path}): ${tool.answer.en}`),
  "",
  `- [Privacy](${publicBase}/privacy): How Wemute keeps supported image work on the visitor's device.`,
  `- [About](${publicBase}/about): Product principles and the scope of Wemute Web.`,
  "",
].join("\n"));

const publisher = process.env.ADSENSE_PUBLISHER_ID?.trim();
const adsPath = path.join(client, "ads.txt");
if (/^pub-\d+$/.test(publisher ?? "")) {
  writeFileSync(adsPath, `google.com, ${publisher}, DIRECT, f08c47fec0942fa0\n`);
} else {
  rmSync(adsPath, { force: true });
}

console.log(`Generated ${INDEXABLE_PATHS.length} public pages (${site.indexable ? site.origin : "safe noindex preview"}).`);
