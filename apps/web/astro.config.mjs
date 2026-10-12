import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";

// A public build must name its canonical origin. Without one the site is built
// as a noindex preview (see src/lib/site.ts) instead of guessing a domain.
const configured = process.env.WEMUTE_SITE_URL?.trim();
if (configured) {
  const url = new URL(configured);
  const local = ["localhost", "127.0.0.1"].includes(url.hostname);
  if (url.protocol !== "https:" && !(local && url.protocol === "http:")) {
    throw new Error("WEMUTE_SITE_URL must use HTTPS (HTTP is allowed only for localhost)");
  }
}

export default defineConfig({
  site: configured || "https://wemute.entropinia.com",
  outDir: "dist/client",
  trailingSlash: "never",
  build: { format: "directory" },
  integrations: [
    react(),
    sitemap({
      i18n: { defaultLocale: "en", locales: { en: "en", zh: "zh-CN" } },
      filter: (page) => !/\/(404|zh\/404)\/?$/.test(page),
    }),
  ],
  vite: {
    // ffmpeg.wasm starts its own module worker; pre-bundling breaks that URL.
    optimizeDeps: { exclude: ["@ffmpeg/ffmpeg", "@ffmpeg/util"] },
    worker: { format: "es" },
  },
});
