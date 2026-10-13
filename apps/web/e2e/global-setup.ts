import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { FFMPEG_CORE_BASE } from "../src/lib/media";
import { ENGINE_DIR, FIXTURE_DIR, MAKE_SCRIPT } from "./paths";

export const ENGINE_FILES = ["ffmpeg-core.js", "ffmpeg-core.wasm"];

async function cacheEngine() {
  mkdirSync(ENGINE_DIR, { recursive: true });
  const version = /@ffmpeg\/core@([^/]+)/.exec(FFMPEG_CORE_BASE)![1];
  for (const name of ENGINE_FILES) {
    const file = path.join(ENGINE_DIR, `${version}-${name}`);
    if (existsSync(file)) continue;
    const response = await fetch(`${FFMPEG_CORE_BASE}/${name}`);
    if (!response.ok) throw new Error(`Could not fetch ${name}: ${response.status}`);
    writeFileSync(file, Buffer.from(await response.arrayBuffer()));
  }
}

export default async function globalSetup() {
  // Drop fixture sets made by older versions of make.sh.
  const parent = path.dirname(FIXTURE_DIR);
  for (const entry of readdirSync(parent)) {
    const dir = path.join(parent, entry);
    if (entry.startsWith("wemute-e2e-fixtures-") && dir !== FIXTURE_DIR) rmSync(dir, { recursive: true, force: true });
  }
  if (!existsSync(path.join(FIXTURE_DIR, ".complete"))) {
    rmSync(FIXTURE_DIR, { recursive: true, force: true });
    console.log(`Generating e2e fixtures in ${FIXTURE_DIR} …`);
    execFileSync("bash", [MAKE_SCRIPT, FIXTURE_DIR], { stdio: ["ignore", "ignore", "inherit"] });
  }
  if (!process.env.E2E_LIVE_CDN) await cacheEngine();
}
