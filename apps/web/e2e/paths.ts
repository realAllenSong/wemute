import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const E2E_DIR = path.dirname(fileURLToPath(import.meta.url));
export const MAKE_SCRIPT = path.join(E2E_DIR, "fixtures", "make.sh");

/** Fixtures are regenerated whenever make.sh changes. */
function scriptHash(): string {
  return createHash("sha1").update(readFileSync(MAKE_SCRIPT)).digest("hex").slice(0, 10);
}

export const FIXTURE_DIR = process.env.WEMUTE_E2E_FIXTURES ?? path.join(tmpdir(), `wemute-e2e-fixtures-${scriptHash()}`);
/** Local copy of the FFmpeg core the site loads from jsDelivr. */
export const ENGINE_DIR = path.join(tmpdir(), "wemute-e2e-ffmpeg-core");
