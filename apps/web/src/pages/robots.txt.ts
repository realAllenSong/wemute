import type { APIRoute } from "astro";
import { INDEXABLE } from "../lib/site";

// Answer engines are welcome: they can only cite pages they are allowed to read.
const AI_CRAWLERS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot", "Google-Extended", "Applebot-Extended", "Bingbot"];

export const GET: APIRoute = ({ site }) => {
  const body = INDEXABLE
    ? [
        "User-agent: *",
        "Allow: /",
        "",
        ...AI_CRAWLERS.flatMap((agent) => [`User-agent: ${agent}`, "Allow: /", ""]),
        `Sitemap: ${new URL("/sitemap-index.xml", site)}`,
        "",
      ].join("\n")
    : "User-agent: *\nDisallow: /\n";
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
