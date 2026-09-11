# Prepare 0.5 verification

## Mac and Portable evidence

Parent execution: debug UI-contract checks, warnings-as-errors release build,
strict-concurrency build, release UI-contract and stress checks passed locally.
Native full checks + stress: 10.62 seconds, 369,573,888 bytes maximum RSS on this
Mac. This includes synthetic rendered and stress workloads, not a worst-case
memory guarantee. Peak footprint reported separately by time: 136,709,056 bytes.
These are different metrics and must not be substituted for one another.

Native package: executable 1,162,880 bytes; app files 1,607,206 bytes;
ZIP 682,160 bytes. All strict decimal budgets pass. Signature verified locally;
ad-hoc only, not notarized. This session's AX helper failed to obtain reliable
window controls (including a helper crash); no new GUI export or minimum-window
pass is claimed. Native engine and Workspace contract checks passed. Website
screenshot is explicitly labeled as the older v0.4 workbench.

Portable package after README update: expanded 40,494 bytes; ZIP 17,173 bytes.
Tests: pure geometry/PDF/input/power tests and 12 Chromium/Firefox browser tests
passed locally. Power tests include custom DPI, threshold whitening, per-page
mutation invalidation and three sequential 20-page synthetic batches per browser.
Independent PyMuPDF checks validate split order, rendered pixels, grayscale,
white padding, A4/Letter geometry and PDF cross-reference correctness.
No-network request tests run with local file URLs. Browser allocations and
extensions are not under application control; bounded input is not a hard RSS cap.

GitHub source 01204fecf21fea71c756630bf21d6d20ed01bc52:
- Windows/Linux Chromium and Firefox CI: run 34586325094, success.
- macOS CI: run 34586325121, success.

## Website

Redesigned dark/light editorial page; no runtime library, webfont or analytics.
OS classifier tests include Android precedence over Linux, iPad exclusion and
unknown fallback. User selection overrides detection; no automatic download.
Browser checks at 1440, 768, 390 and 320 px: no horizontal overflow, platform
filters, keyboard navigation, no-JS downloads, documentation and no JS errors.
Desktop/mobile screenshots reviewed; hero spacing and installation-note sizes
corrected. Screenshot can be opened full size.

SEO: canonical/social descriptions, SoftwareApplication schema, root robots.txt,
generated sitemap and CI drift checks. No fake ratings or ranking guarantees.

## Limits

100 roadmap entries are architecture proposals plus a small implemented slice,
not 100 shipped features. Android has its own verification record. Store files
are structural foundations, not approvals. No password encryption, OCR, PDF input,
AI background segmentation, native Windows/Linux binary or Intel Mac release is
claimed. Hippocratic 3.0 core is ethical-source, not OSI-approved open source.

## Final checked source and device evidence

Source fb0555bb8e98ca980b0c699c0b669319e4a0af8c passes Android CI
34589813446 (API 28 and API 36, 17 runtime tests each), macOS CI 34589813411,
and Windows/Linux CI 34589813399. Independent focused review passed the three
Android fixes at 6693926. The later harness-only change requests raw `am instrument
-w -r` output, preserving the explicit success-code check.

Both Android CI APKs were downloaded and matched the locally built unsigned APK
byte-for-byte: 24,796 bytes, SHA-256
0dafc2a3c664c182a5693836652f4d3d001994bde6a91aed08eaad1cd9a8d0bc.
The manifests request no permissions. Both instrumentation reports explicitly
show `OK (17 tests)` and `INSTRUMENTATION_CODE: -1`. APK alignment, partial-prefix
rejection, actual PDF rendering, cancellation, cleanup and each settings-change
invalidation pass. Earlier failed-run notes above are retained as history, not
current release blockers. No production signing or physical-device verification
is implied; unsigned Android is a developer artifact, not a normal install.
