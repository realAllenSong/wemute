import type { APIRoute } from "astro";
import { localePath } from "../data/locale";
import { TOOLS } from "../data/tools";

export const GET: APIRoute = ({ site }) => {
  const sections = TOOLS.map((tool) =>
    [
      `## ${tool.h1.en}`,
      "",
      `URL: ${new URL(localePath("en", tool.slug), site)}`,
      `Chinese: ${new URL(localePath("zh", tool.slug), site)}`,
      "",
      tool.answer.en,
      "",
      "Steps:",
      ...tool.steps.map((step, index) => `${index + 1}. ${step.en}`),
      "",
      "FAQ:",
      ...tool.faqs.flatMap((faq) => [`- Q: ${faq.q.en}`, `  A: ${faq.a.en}`]),
      "",
    ].join("\n"),
  );
  const body = ["# Wemute — full tool reference", "", "All tools run locally in the browser; files are never uploaded.", "", ...sections].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
