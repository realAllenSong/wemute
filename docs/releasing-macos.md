# Releasing Wemute for macOS

Wemute's release scripts build an Apple Silicon application, audit embedded
code and licenses, sign every Mach-O item inside-out, enable Hardened Runtime,
notarize both the app and its DMG, staple tickets, and produce SHA-256 files.

## One-time Apple setup

1. Join the Apple Developer Program and install a **Developer ID Application**
   certificate in the login keychain.
2. Confirm the identity with `security find-identity -p codesigning -v`.
3. Store notarization credentials in Keychain; never put the password in this
   repository:

   ```sh
   xcrun notarytool store-credentials "wemute-notary" \
     --apple-id "you@example.com" \
     --team-id "YOUR_TEAM_ID" \
     --password "APP_SPECIFIC_PASSWORD"
   ```

4. Generate a Sparkle EdDSA update key. Keep the private key in Keychain and
   back it up securely; the printed public key is used at build time:

   ```sh
   scripts/build-sparkle-macos.sh
   build/runtime/sparkle/bin/generate_keys --account wemute
   ```

## Local package test

This creates an ad-hoc signed DMG without contacting Apple:

```sh
scripts/package-macos.sh --local
```

## Public release

```sh
export WEMUTE_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export WEMUTE_NOTARY_PROFILE="wemute-notary"
export WEMUTE_SPARKLE_PUBLIC_KEY="PUBLIC_KEY_PRINTED_BY_GENERATE_KEYS"
scripts/package-macos.sh
```

Outputs are written to `dist/releases`. A public release must not bypass
`scripts/audit-macos-bundle.sh`; it rejects Homebrew-linked code, GPL/nonfree
FFmpeg configurations, x265, missing notices, invalid signatures, and missing
notarization tickets.

The release should still be installed and exercised from the DMG in a fresh
macOS account with no Homebrew, Python, or model cache before publishing.

`appcast.xml` is emitted beside the release archives and is itself backed by
EdDSA-signed update archives. Upload it as a GitHub Release asset so the stable
feed URL remains constant. Name the release tag `v<version>` so the generated
archive URLs resolve. Also upload `Wemute.dmg`, the same DMG under a fixed name: the
website's **Download for Mac** button links to
`releases/latest/download/Wemute.dmg`, which downloads it directly. Sparkle retains the latest three versions in its
feed; rollback is performed as a fix-forward release of the last known-good
source with a higher build number, because secure clients correctly reject
downgrades.

For an emergency rollback, rebuild the last known-good source with a higher
`WEMUTE_BUILD_NUMBER` (for example `2026081901`) while keeping the user-facing
version intentional. Sparkle then treats it as a forward, signed recovery
instead of accepting an attacker-friendly downgrade.
