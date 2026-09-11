# Cross-platform qualification

A shared source module does not prove that a platform works. This document
separates execution targets from package formats and commercial signing.

## Existing releases

- macOS Apple Silicon: native Swift/Apple-framework image converter, macOS14+.
  Ad-hoc signed, not notarized. Tests include real PDF rendering, export
  exclusivity, byte budgets, source preservation and bounded batch stress.
- Windows/Linux/macOS desktop browsers: offline extracted HTML bundles,
  not native executable packages. Chromium and Firefox run file-URL tests.
- Android: native framework-only source and unsigned developer APK. API28/36
  emulator tests are separate from physical-device/store qualification.
- Node CLI: requires a separately installed Node22+ runtime. A source ZIP
  with bundled libraries is not a standalone native executable.
- iOS/iPadOS: no supported product release. No claim based on desktop HTML.

## Additional qualification in this branch

The macOS x86_64 converter cross-compiles with strict Swift concurrency and
passes the full checks/stress binary under Rosetta on Apple Silicon. CI also
runs build, behavior, rendering, stress, size and signature gates on
`macos-15-intel`. A release must cite the actual successful CI run before
claiming native Intel qualification. Rosetta alone is not physical Intel
hardware evidence. Neither target is Apple-notarized.

PDF page operations share the same adapter between Node and a disposable
browser worker. CLI tests run on Linux, Windows and macOS; browser tests run
on Windows and Linux. ARM Linux/Windows, mobile browsers and iOS are not
implied by JavaScript portability. A browser worker deadline is not a hard
OS memory sandbox.

## Platform decisions

No Electron runtime, synthetic native shell, automatic PDF association or
unsupported universal binary is introduced merely for a platform badge.
AppImage/Flatpak/Snap/MSIX and store submission wait for qualified native
hosts and a real distribution need. Existing bundle IDs, source URLs and
stable tags are preserved.

## Intel qualification result

The macos-15-intel runner passed debug, release/stress, strict-concurrency,
packaging and signature checks. Its x86_64 0.5.0 app was downloaded, checksum
verified, extracted, signature-verified and launched under Rosetta locally.
It is offered as an Intel preview alongside the 0.7 PDF beta, not silently
added to the established stable download. It remains ad-hoc signed and
not notarized. No PDF-input feature is added to this native image app.
