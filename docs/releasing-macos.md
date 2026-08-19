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

## Local package test

This creates an ad-hoc signed DMG without contacting Apple:

```sh
scripts/package-macos.sh --local
```

## Public release

```sh
export WEMUTE_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export WEMUTE_NOTARY_PROFILE="wemute-notary"
scripts/package-macos.sh
```

Outputs are written to `dist/releases`. A public release must not bypass
`scripts/audit-macos-bundle.sh`; it rejects Homebrew-linked code, GPL/nonfree
FFmpeg configurations, x265, missing notices, invalid signatures, and missing
notarization tickets.

The release should still be installed and exercised from the DMG in a fresh
macOS account with no Homebrew, Python, or model cache before publishing.
