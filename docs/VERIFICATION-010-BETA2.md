# Filecraft 0.10.0-beta.2 verification

Status: **published as a GitHub prerelease**, `v0.10.0-beta.2`, tag
[v0.10.0-beta.2](https://github.com/Filecraft/Filecraft/releases/tag/v0.10.0-beta.2),
created at the qualified source commit
`218527279dea2de542c68890e433675c1642683b` (`distribution/consumer-0.10-beta2`).

Both `v0.10.0-beta.1` and `v0.10.0-beta.2` are prereleases, so `/releases/latest`
is unaffected. The current-beta entry point is the website and README.

## Verified from the recorded evidence

- Native CI [run 34669609614](https://github.com/Filecraft/Filecraft/actions/runs/34669609614)
  passed all four consumer jobs and the manifest gate at the source above.
- The four assembled artifacts re-hash to the values recorded in
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
  `staple_valid: false` for both architectures.

## Exact-final-artifact macOS GUI qualification

The last recorded blocker was macOS-architecture GUI evidence for the exact
candidate artifacts. It is resolved.

The blocking condition was a host privacy permission, not the product:
Accessibility and Screen Recording for the host application are now granted, and
the harness capability gate passes on a live probe. The probe only accepts a
synthetic F13 keycode, a key no human presses during a run, so the user's own
typing can never be mistaken for delivered input.

`distribution/macos/test-installed-gui.py` was then run against the two
candidate DMGs exactly as assembled, and the verbatim records are committed
under `docs/qualification/`:

| artifact | sha256 | bundle | integration | result |
| --- | --- | --- | --- | --- |
| `Filecraft-0.10.0-beta.2-macos-arm64.dmg` | `9c25a69b…` | `io.github.filecraft.desktop`, arm64 | native (Apple Silicon host) | PASS |
| `Filecraft-0.10.0-beta.2-macos-x86_64.dmg` | `b430cc66…` | `io.github.filecraft.desktop`, x86_64 | **Rosetta 2 translation** | PASS |

Each run mounted the DMG under test, replaced the installed application, passed
`codesign --verify --deep --strict`, asserted the `lipo` architecture and bundle
id, ran the frozen runtime check, launched the installed bundle, then drove the
real GUI: import through the open panel, export a new copy through the save
panel, exported pixels compared with the source, original file byte-unchanged,
clean `Cmd+Q` quit (`returncode: 0`), relaunch, and a second clean quit.

Honest limits of this evidence:

- The Intel artifact was exercised on Apple Silicon under **Rosetta 2**, not on
  Intel hardware. It is recorded as `integration: rosetta-translated` and is
  **not** native Intel evidence.
- Both builds remain ad-hoc signed and not notarized; `gatekeeper_accepted` is
  `false`. No Developer ID signature or notarization exists.
- The journey uses a synthetic 80×60 PNG. It is a real end-to-end GUI path, not
  a claim about every input type, and not a security certification.

## Public artifact verification after publication

Every published asset was downloaded anonymously (no credentials) and checked
against the published `release-manifest.json`:

- The four artifacts match their recorded byte size and SHA-256.
- All four `.sha256` sidecars verify with `shasum -a 256 -c` on macOS.
- The tag resolves through the API to the annotated tag object
  `b6af9eef…` and then to commit `2185272…`, matching `source_commit` in the
  manifest.

## Live site verification after deployment

The website was published and then checked from the outside, anonymously, on the
live origin rather than against the local build:

- `/download/` presents the current beta and no longer offers a beta.1 download.
- All four cards render, each labelled with its real format (Download DMG,
  Download EXE, Download DEB) instead of every artifact being called a ZIP.
- Every advertised link resolves with HTTP 200, and the bytes served hash to the
  checksum advertised on the page, which is the digest read back from the
  published sidecar.
- The filter buttons, the card platform values and `platform.js` use one
  platform vocabulary, so a macOS visitor sees the macOS installers.
- `/releases/` still marks the current release and keeps the earlier betas, so
  the historical archive is intact.

The site's own `Static site checks` workflow passed on the publishing commit
(`db913c6`), and the deployed result was verified live rather than assumed.

## Consumer download experience verified live

The deployed site was then driven as an ordinary anonymous visitor with a real
browser, not inspected as source:

- A macOS visitor reaches the download page and is shown only the two macOS
  DMGs, with the Windows and Linux cards hidden and the macOS filter active. A
  Windows or Linux visitor is shown one installer each. An Android, iPhone or
  unrecognised visitor is shown every package with an explicit note that no
  package exists for them, and never a misleading native installer.
- Nothing downloads until a call to action is clicked: zero asset requests and
  zero downloads were observed on load in every scenario.
- The real download was exercised end to end. Clicking the Apple Silicon card
  in a real browser produced `Filecraft-0.10.0-beta.2-macos-arm64.dmg`,
  30,216,361 bytes, SHA-256 `9c25a69b…`, which matches the published manifest,
  the arm64 architecture and version `0.10.0-beta.2`.
- Mobile viewports (390 px and 412 px) do not overflow, dark mode is a real
  painted theme rather than a declaration, the theme toggle switches both ways,
  and with JavaScript disabled every package stays listed and linked.
- No ZIP or portable Suite package is offered anywhere for this release; the
  historical archive still carries the earlier betas and marks the current one.

One consumer-facing defect was found and fixed. The landing page's primary
button was generated from the Windows asset, so on macOS and Linux the most
prominent download offered another platform's installer; only the download page
adapted. The hero now carries per-platform targets generated from the published
inventory and swaps to the visitor's own build, with the Windows button kept as
the static default so visitors without JavaScript see exactly what they saw
before (`filecraft.github.io` commit `30d6d40`).

The macOS architecture choice is a pure, tested rule. Chromium reported
`architecture: x86` on a withheld hint set even on this Apple Silicon Mac, so a
hint is trusted only when it reports `arm`; the GPU renderer decides first and
the fallback is Apple Silicon, which the label names. A regression test covers
that decision table and guards the hero against reverting to one platform.

## Two compatibility notes on the published assets

Both are naming/encoding fixes only. No artifact byte changed and no digest
changed.

- **Debian asset name.** GitHub rewrites `~` to `.` in release asset names, so
  the published file is `filecraft_0.10.0.beta.2-1_ubuntu24.04_amd64.deb` and
  not `filecraft_0.10.0~beta.2-1_ubuntu24.04_amd64.deb`. The package version
  inside the `.deb` is unchanged (`0.10.0~beta.2-1`, still the Debian `~`
  pre-release ordering). The manifest `filename` and `download_url` now name the
  published file, and the sidecar was rewritten to match.
- **Windows sidecar line endings.** The Windows-built sidecar was uploaded with
  CRLF, which makes `shasum -c` fail on macOS and Linux. This release's Windows
  setup sidecar was re-uploaded with LF line endings and the identical digest.
  The historical `v0.10.0-beta.1` Windows sidecar was left untouched.

## Live site correction

The deployed download page had used two vocabularies: the macOS filter button
and `platform.js` detection used `mac`, while the inventory cards render
`macos`. A Mac visitor was therefore told "No mac package in this release
inventory" and the macOS filter never filtered. Fixed, with a regression test
that fails if the button, card and detection vocabularies drift apart
(`filecraft.github.io` commit `d5e1e43`), and verified against the live site.

## The Mac architecture is now a choice, not a guess

The landing hero and the download page led with one macOS build chosen from a
best-effort signal: the GPU renderer when readable, otherwise a client hint
that reports the default `x86` whenever it is withheld. The guess was invisible
and final, so a Mac visitor could be served the wrong architecture with no way
back. Both places now lead with the likely build and carry an Apple Silicon /
Intel chooser beside it, driven by the one shared decision. Choosing an
architecture repoints the hero target and label, leads the download list with
the matching build and marks it recommended; the other build stays in the
list, one click away.

The static markup is unchanged for visitors without JavaScript: the hero keeps
the Windows default and the chooser stays hidden, and every published package
remains listed and linked. No new translation was invented; the chooser group
is named from the existing localised "Downloads" string.

Two real defects were found and fixed while wiring this up: `platform.js` had a
duplicated declaration that made the page script fail to parse, and the reorder
used a static query snapshot, so the chosen build landed second in the list
rather than first.

Verified in a real browser against a local build and then against the live
origin after deployment (`filecraft.github.io` commit `2a73f23`):

- A Mac visitor sees the chooser; one click switches the hero and the list in
  both directions, and clicking the chooser never starts a download by itself.
- The layout holds at 1440 px and 390 px with no horizontal overflow, and the
  selected chip inverts correctly in light and dark mode.
- Windows, Linux, Android, iOS and unknown visitors keep the plain platform
  default with the chooser hidden.
- The deployed `platform.js` is byte-identical to the committed one, and both
  DMGs fetched anonymously from the advertised links match the manifest size
  and SHA-256 exactly (`...arm64.dmg` 30,216,361 bytes, `...x86_64.dmg`
  31,705,887 bytes).
- Covered by a new behavioural regression test in the site CI workflow.

## Previously verified releases

- The public `v0.10.0-beta.1` release was re-verified independently on
  2026-09-12: all seven assets match their sidecars, GitHub's recorded digests
  and sizes, and the website inventory.
- The live site was re-verified as byte-identical to its deployed commit, with
  correct per-platform filtering, zero cookies, zero third-party requests and
  resolving installer links.

## Must not be claimed

The published artifacts are unsigned and not notarized (macOS ad-hoc only);
Gatekeeper is expected to reject the macOS builds. Nothing in this record is a
signature, an independent security certification, native Intel execution, or a
fidelity guarantee. Receipts compare bytes; they do not certify authorship,
safety, accessibility or portal acceptance.
