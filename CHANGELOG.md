# Changelog

What each Wemute release added and fixed. Downloads are on [GitHub Releases](https://github.com/realAllenSong/wemute/releases).

## v0.7.6

- **Settings › About**, [NOTICE](NOTICE) and the [CLA](CLA.md) state the
  copyright holder's legal name.

## v0.7.5

- **Settings › About** names realAllenSong as the copyright holder, matching
  [NOTICE](NOTICE). Contributors now sign a [Contributor License
  Agreement](CLA.md) on their first pull request.

## v0.7.4

- **Wemute for AI agents.** `wemute mcp` is an MCP server, so Claude Code,
  Codex, Cursor, Claude Desktop and other agents can read and convert files
  with Wemute. **Settings › Integrations** also installs a `wemute` skill
  that teaches Claude Code and Codex the command line. See
  [docs/cli.md](docs/cli.md#wemute-mcp--wemute-for-ai-agents).
- `wemute convert --out DIR` saves one run's outputs in a folder you choose.

## v0.7.3

- **Erase no longer quits the app.** Pressing **Erase** after painting could
  crash Wemute. The mask is now drawn from your brush strokes at the photo's
  full size, without a large on-screen canvas.

## v0.7.2

- **Downloads that work everywhere.** The app now carries its own HTTPS
  certificates. Before, Macs without Homebrew could not download models or
  components.
- **Downloads that never hang.** A stalled connection gives up after 30
  seconds and moves on to a mirror. The Erase and Upscale models now come
  from Wemute's own GitHub mirror first.
- **`wemute models` and `wemute doctor`:** install models from the command
  line, and check what works on this Mac.

## v0.7.1

- **One place for every tool:** the toolbar's Tools menu and ⌘K search showed the same tools, so the Tools menu is gone. **Find a tool ⌘K** searches every tool, and shows the full list when you type nothing.

## v0.7.0

- **First signed release.** Wemute is signed with a Developer ID and notarized
  by Apple, and it updates itself through Sparkle.
- **`wemute extract`** turns any file or folder into Markdown, text or JSON
  lines for language models. It reads:
  - PDF pages and tables, with OCR for scanned pages;
  - Word headings, Excel sheets, and slides with their speaker notes;
  - screenshots;
  - call recordings, with speaker labels;
  - e-mails with their attachments, and archives.

  See [For scripts and AI agents](#for-scripts-and-ai-agents).
- **Subtitles and read-aloud through ThunderTalk.** Subtitles can be SRT,
  VTT, a transcript, or a transcript that labels each speaker. Transcription
  uses the most accurate model you have downloaded. Read-aloud uses VoxCPM2.
- **Better photo tools:**
  - ID photos and the new portrait blur use Apple's subject cut-out, and keep
    loose hair clean on red and blue backdrops.
  - Erase no longer leaves a ghost or a dark smear on larger objects.
- **Built into macOS:** Finder Quick Actions, a Shortcuts action, a `wemute`
  shell command, a Settings window, the native menu bar, and ⌘K search.
