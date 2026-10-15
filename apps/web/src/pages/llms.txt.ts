import type { APIRoute } from "astro";
import { localePath } from "../data/locale";
import { CATEGORY_LABEL, CATEGORY_ORDER, toolsIn } from "../data/tools";
import { MAC_APP_LINES } from "../data/mac";

export const GET: APIRoute = ({ site }) => {
  const url = (path: string) => new URL(path, site).toString();
  const lines = [
    "# Wemute",
    "",
    "> Free file conversion tools that run entirely in the visitor's web browser. Files are converted on the visitor's own device with WebAssembly (FFmpeg, libheif) and the browser's image engine; file contents and names are never uploaded. No account, no watermark. Available in English and Simplified Chinese (/zh/).",
    "",
    "Key facts:",
    "- Price: free.",
    "- Privacy: processing happens locally; nothing is uploaded.",
    "- Batch: many files at once; results download individually or as one ZIP.",
    "- Video/audio: powered by FFmpeg compiled to WebAssembly; H.264 sources are remuxed to MP4 without re-encoding.",
    "",
    ...CATEGORY_ORDER.flatMap((category) => [
      `## ${CATEGORY_LABEL[category].en} tools`,
      "",
      ...toolsIn(category).map((tool) => `- [${tool.name.en}](${url(localePath("en", tool.slug))}): ${tool.answer.en}`),
      "",
    ]),
    ...MAC_APP_LINES,
    "## Optional",
    "",
    `- [Full tool reference](${url("/llms-full.txt")}): steps and FAQs for every tool.`,
    `- [Privacy policy](${url("/privacy")})`,
    `- [About](${url("/about")})`,
    "",
  ];
  return new Response(lines.join("\n"), { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
