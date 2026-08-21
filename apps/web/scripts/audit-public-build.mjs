#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { INDEXABLE_PATHS, metadataForPath } from "../src/site-content.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const client = path.join(root, "dist", "client");
const configured = Boolean(process.env.WEMUTE_SITE_URL?.trim());
const titles = new Set();

function pagePath(pathname) {
  return pathname === "/" ? path.join(client, "index.html") : path.join(client, pathname.slice(1), "index.html");
}

function requireText(html, value, pathname) {
  if (!html.includes(value)) throw new Error(`${pathname} is missing: ${value}`);
}

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

for (const pathname of INDEXABLE_PATHS) {
  const file = pagePath(pathname);
  if (!existsSync(file)) throw new Error(`Missing route output: ${file}`);
  const html = readFileSync(file, "utf8");
  const metadata = metadataForPath(pathname);
  requireText(html, `<title>${escapeHtml(metadata.title)}</title>`, pathname);
  requireText(html, `content="${escapeHtml(metadata.description)}"`, pathname);
  requireText(html, 'rel="canonical"', pathname);
  requireText(html, 'property="og:title"', pathname);
  requireText(html, 'id="wemute-structured-data"', pathname);
  requireText(html, 'type="application/ld+json"', pathname);
  requireText(html, "<h1>", pathname);
  if (titles.has(metadata.title)) throw new Error(`Duplicate title: ${metadata.title}`);
  titles.add(metadata.title);
}

const robots = readFileSync(path.join(client, "robots.txt"), "utf8");
if (configured) {
  requireText(robots, "Allow: /", "robots.txt");
  requireText(robots, "Sitemap:", "robots.txt");
  if (!existsSync(path.join(client, "sitemap.xml"))) throw new Error("Configured build is missing sitemap.xml");
} else {
  requireText(robots, "Disallow: /", "robots.txt");
  if (existsSync(path.join(client, "sitemap.xml"))) throw new Error("Preview build must not publish a sitemap");
  for (const pathname of INDEXABLE_PATHS) requireText(readFileSync(pagePath(pathname), "utf8"), "noindex, nofollow", pathname);
}

if (!existsSync(path.join(client, "llms.txt"))) throw new Error("Missing llms.txt");
if (!process.env.ADSENSE_PUBLISHER_ID && existsSync(path.join(client, "ads.txt"))) {
  throw new Error("ads.txt must not be generated with a placeholder publisher ID");
}

console.log(`SEO build audit passed for ${INDEXABLE_PATHS.length} unique routes.`);
