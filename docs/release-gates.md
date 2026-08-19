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
- Validate outputs in QuickTime, Preview, VLC/IINA and a fresh ffprobe pass.
- Add update signing, rollback and a crash-safe migration for queue/settings data.

## Product gate

- First conversion succeeds without onboarding or an account.
- Batch users can set one result per media group in one action.
- Advanced settings remain closed by default and explain their visible outcome.
- No telemetry is added until its exact event list and opt-out behavior are documented.
- Watermark/object removal is described as editing content the user has rights to modify.
