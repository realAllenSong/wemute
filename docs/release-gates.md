# Wemute release gates

## Desktop Alpha gate

- Core conversion tests, worker crash isolation and queue recovery pass.
- The packaged Apple Silicon app starts from Finder with an interactive-shell-free PATH.
- Image output preserves orientation and applies resize, quality and corner settings correctly.
- A group format change updates every non-running item; an individual item can still override it.
- No conversion overwrites its source or leaves a successful-looking partial output.

## Public macOS gate

- Bundle an audited LGPL-compatible FFmpeg/FFprobe runtime and required notices.
- Add application icon, Developer ID signing, hardened runtime, notarization and a DMG.
- Produce a dependency/license inventory and source-offer material where required.
- Reject any bundle containing `libx265`; macOS HEIC input/output uses the
  system ImageIO codec through `/usr/bin/sips`, so no HEVC encoder library is
  embedded in the application.
- Validate outputs in QuickTime, Preview, VLC/IINA and a fresh ffprobe pass.
- Add update signing, rollback and a crash-safe migration for queue/settings data.

The automated path is `scripts/package-macos.sh`. `--local` produces a test
DMG; the default path requires a Developer ID identity and a `notarytool`
Keychain profile, signs nested code explicitly, notarizes/staples the app and
DMG, and runs `scripts/audit-macos-bundle.sh` before release.

## AI package gate

- Every remote artifact has an allow-listed HTTPS URL, exact byte count, SHA-256,
  version and license in the bundled manifest.
- The user sees model size and license before first download; no model arrives as
  a side effect of opening a file.
- Interrupted, oversized and checksum-mismatched downloads leave no active or
  success-looking package behind.
- AI runs outside the UI process and writes to a temporary output before the same
  atomic finalize step used by conversions.
- Core ML compilation cache is reusable, and a CPU fallback produces a compatible
  output when Core ML is unavailable.
- Real-ESRGAN and future native helper binaries are rebuilt, signed, notarized and
  shipped with complete notices before public distribution.
- Vocal-separation weights are individually license-audited; the license of the
  surrounding Python package is not treated as the model license.

## Product gate

- First conversion succeeds without onboarding or an account.
- Batch users can set one result per media group in one action.
- Advanced settings remain closed by default and explain their visible outcome.
- No telemetry is added until its exact event list and opt-out behavior are documented.
- Watermark/object removal is described as editing content the user has rights to modify.
