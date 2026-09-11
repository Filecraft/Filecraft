# Release checklist

Releases are deliberate maintainer actions, not automatic publications on push.
The macOS CI workflow checks source and packaging. The official website is
https://filecraft.github.io/ and publishes `main:/` from the dedicated
`gonisulaimann/gonisulaimann.github.io` repository. This app repository keeps
a legacy landing-page redirect; do not edit its old assets to update the live site.

1. Update the version in `scripts/package.py`, README, CHANGELOG and website.
2. Run `swift run PrepareChecks`, release checks, warnings-as-errors and stress
   checks. Record machine, compiler, fixture workload and real measured values.
3. Run the app repository redirect check (`python3 scripts/check-site.py`).
   In the dedicated site repository, regenerate HTML docs and run its site
   checker. Preview the site at narrow and wide widths; check keyboard focus,
   anchors, download URLs and reduced motion.
   Run `node scripts/test-site.cjs` and `python3 scripts/test_release_budget.py`.
4. `bash scripts/package.sh`; inspect the bundle version and arm64 architecture.
   Packaging rejects a binary ≥2,000,000 bytes, app ≥3,000,000 bytes, or ZIP
   ≥1,500,000 bytes. Inspect `build/release-size.json`. Do not loosen budgets
   silently. Keep marketing images outside the app bundle.
5. Run `codesign --verify --strict build/Prepare.app`. Launch the app and test
   add, reorder, rotate, margins, compare, cancellation and new-file export.
6. Unzip into a temporary directory and repeat signature and bundle checks.
   Confirm LICENSE, NOTICE and icon resources are included.
7. Review `git diff --cached` for credentials, private samples and generated
   artifacts. Require green CI before publishing release assets.
8. Tag the exact reviewed commit and publish the ZIP, checksum, LICENSE and
   verification report with `gh release create`. Explain signing status in
   the release notes. Download the assets again and check SHA-256.
9. Verify the public repository, release and GitHub Pages URL independently.

## Signing status

Current builds use an ad-hoc signature and are **not notarized**. Do not claim
otherwise or tell users to disable Gatekeeper globally. Users may need to
approve the app through System Settings → Privacy & Security after attempting
to open it. Corporate policies may forbid running it; building locally is an
alternative, not a policy bypass.

`SIGN_IDENTITY` can select a valid installed Developer ID certificate when
packaging. That only signs the app. Notarization, ticket stapling and fresh
Gatekeeper assessment must be completed separately before changing claims.
Do not publish signing credentials or embed credentials in CI. Intel/universal
builds require their own hardware testing and correct asset architecture names.

## Cross-platform gates for 0.5 and later

Run `npm --prefix portable ci`, `npm --prefix portable test`,
`python3 scripts/package_portable.py`, and `python3 scripts/test_portable_budget.py`.
Verify Windows and Linux CI artifacts and extracted contents, not just ZIP hashes:
ZIP host-system metadata can differ while file contents match exactly.
Use an independent PDF renderer for Portable output. Preserve desktop-browser
prerequisites and never rename the ZIP to imply a native binary.

For Android run `python3 android/build.py` and actual API 28 / 36 emulator tests.
Compile success is insufficient: byte-limit exceptions may be swallowed by native
PDF writers, and APK packaging constraints differ between API levels. Check every
accepted PDF and resources.arsc storage/alignment. Never publish disposable test
signatures. Owner signing, physical devices and store/AAB gates are separate.

Publish only after independent review and exact-source platform CI pass. Download
public artifacts again, validate SHA-256, signature/manifest and source content.
Only then deploy the dedicated site with new links. Keep the app's legacy redirect.
