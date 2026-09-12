# Filecraft 0.10.0-beta.2 candidate verification

Status: **candidate qualified in CI, not published.** There is no `v0.10.0-beta.2`
tag and no release. `v0.10.0-beta.1` remains the current public release.

Qualified source: `218527279dea2de542c68890e433675c1642683b`
(`distribution/consumer-0.10-beta2`).

## Verified from the recorded evidence

- Native CI [run 34669609614](https://github.com/Filecraft/Filecraft/actions/runs/34669609614)
  passed all four consumer jobs and the manifest gate at the source above.
  Its artifacts are still downloadable and unexpired.
- The four assembled candidate artifacts re-hash to the values recorded in
  `build/qualified-beta2/release-manifest.json` and their `.sha256` sidecars:
  macOS arm64 DMG `9c25a69b…`, macOS x86_64 DMG `b430cc66…`, Windows x64
  setup `08212197…`, Ubuntu 24.04 amd64 DEB `2e3298bf…`.
- Windows installed GUI evidence: `passed: true`, `original_unchanged: true`,
  `quit_relaunch: true`, with screenshots for import, filled save and export,
  under the restricted medium-integrity token (exit code 0).
- Ubuntu 24.04 installed GUI evidence: same result shape under Xvfb/X11 with
  `original_unchanged: true` and `quit_relaunch: true`.
- macOS CI qualification records `installed_runtime_passed: true`,
  `bundle_id: io.github.filecraft.desktop`, `gatekeeper_accepted: false`,
  `staple_valid: false`, `gui_export_tested: false` for both architectures.

## Re-run independently on a maintainer Mac

`distribution/macos/test-install.py` was re-run locally against copies of both
DMGs (the CI evidence was left untouched). Both mounted with the Applications
symlink and Finder layout intact, passed `codesign --verify --deep --strict`
with bundle id `io.github.filecraft.desktop`, and passed the frozen runtime
suite (PDF renderer, AES, image/PDF/archive, preview, rasterization,
exact/optimized auto-fit). Each recorded `gui_export_tested: false`.

`lipo` confirms the two frozen executables really are `arm64` and `x86_64`.
The Intel runtime check ran on an Apple Silicon host and therefore under
Rosetta translation; Rosetta presence was confirmed separately. No Intel
hardware was available for a native Intel run.

## Live site correction

The deployed download page was found to use two vocabularies: the macOS filter
button and `platform.js` detection used `mac`, while the inventory cards render
`macos`. A Mac visitor was therefore told "No mac package in this release
inventory" and the macOS filter never filtered. Fixed, with a regression test
that fails if the button, card and detection vocabularies drift apart
(`filecraft.github.io` commit `d5e1e43`), and verified against the live site.

## Not verified

- The public `v0.10.0-beta.1` release was re-verified independently on
  2026-09-12: all seven assets match their sidecars, GitHub's recorded digests
  and sizes, and the website inventory.
- The live site was re-verified as byte-identical to its deployed commit, with
  correct per-platform filtering, zero cookies, zero third-party requests and
  resolving installer links.

## Remaining blocker before publishing the Mac artifacts

Repository release guidance requires exact-final-artifact GUI
import/export/quit/relaunch evidence per Mac architecture. That has not been
recorded.

The blocking condition is a host privacy permission, not the product. On the
maintainer's Mac the console session is unlocked and an installed Filecraft
window is present, but the process that would drive the GUI reports:

    CGPreflightPostEventAccess    = False
    CGPreflightScreenCaptureAccess = False
    AXIsProcessTrusted            = False

Synthetic OS input cannot be delivered and no screenshot can be captured from
that host process. Granting Accessibility and Screen Recording to the host
application (System Settings → Privacy & Security) would unblock it; the
project does not attempt to bypass these controls. An Intel artifact must be
qualified on Intel hardware or, if it is only exercised under Rosetta, that
must be stated in the evidence.

## Must not be claimed

The candidate is unsigned and not notarized (macOS ad-hoc only); Gatekeeper is
expected to reject it. Nothing in this record is a signature, an independent
security certification or a fidelity guarantee. The download path for consumers
today is `v0.10.0-beta.1` and must not be pointed at these artifacts before the
Mac GUI evidence and public-byte verification exist.
