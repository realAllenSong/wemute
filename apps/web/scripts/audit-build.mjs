#!/usr/bin/env node
// Post-build: write ads.txt for a real publisher and audit every public page.
import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const client = path.join(root, "dist", "client");
const indexable = Boolean(process.env.WEMUTE_SITE_URL?.trim()) && !/localhost|127\.0\.0\.1/.test(process.env.WEMUTE_SITE_URL);

const publisher = process.env.ADSENSE_PUBLISHER_ID?.trim() ?? "";
const adsPath = path.join(client, "ads.txt");
if (/^pub-\d{10,}$/.test(publisher)) writeFileSync(adsPath, `google.com, ${publisher}, DIRECT, f08c47fec0942fa0\n`);
else rmSync(adsPath, { force: true });

// Every generated page: directories holding an index.html (the 404 page aside).
function walk(dir, prefix = "") {
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith("_") || entry.name === "404") continue;
    const page = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (existsSync(path.join(dir, entry.name, "index.html"))) found.push(page);
    found.push(...walk(path.join(dir, entry.name), page));
  }
  return found;
}
const pages = ["", ...walk(client)];
// 26 tools + 3 legal pages + home, in two languages.
const MINIMUM_PAGES = 60;

const failures = [];
const titles = new Map();
for (const page of pages) {
  const file = path.join(client, page, "index.html");
  if (!existsSync(file)) {
    failures.push(`missing ${page || "/"}`);
    continue;
  }
  const html = readFileSync(file, "utf8");
  const title = /<title>([^<]+)<\/title>/.exec(html)?.[1];
  const checks = {
    title: Boolean(title),
    // CJK text carries roughly twice the information per character.
    description: new RegExp(`<meta name="description" content="[^"]{${page.startsWith("zh") ? 25 : 50},}"`).test(html),
    canonical: /<link rel="canonical" href="https?:\/\/[^"]+"/.test(html),
    hreflang: html.includes('hreflang="x-default"'),
    h1: (html.match(/<h1[\s>]/g) ?? []).length === 1,
    jsonLd: html.includes('type="application/ld+json"'),
    robots: indexable ? html.includes('content="index, follow') : html.includes('content="noindex, nofollow"'),
  };
  for (const [name, ok] of Object.entries(checks)) if (!ok) failures.push(`${page || "/"}: ${name}`);
  if (title) {
    if (titles.has(title)) failures.push(`duplicate title "${title}" on ${page} and ${titles.get(title)}`);
    titles.set(title, page);
  }
}

if (pages.length < MINIMUM_PAGES) failures.push(`only ${pages.length} pages generated`);

const robots = readFileSync(path.join(client, "robots.txt"), "utf8");
if (indexable ? !robots.includes("Sitemap:") : !robots.includes("Disallow: /")) failures.push("robots.txt");
if (!existsSync(path.join(client, "llms.txt"))) failures.push("llms.txt");
if (indexable && !existsSync(path.join(client, "sitemap-index.xml"))) failures.push("sitemap");

if (failures.length) {
  console.error(`SEO audit failed:\n- ${failures.join("\n- ")}`);
  process.exit(1);
}
console.log(`SEO audit passed for ${pages.length} pages (${indexable ? "indexable" : "noindex preview"}).`);
