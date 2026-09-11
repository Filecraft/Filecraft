# Prepare 0.4.0 verification

## Automated checks

Parent-run debug `PrepareChecks --ui-contract`, strict release build with
`-warnings-as-errors -strict-concurrency=complete`, and release stress all passed.
Tests render actual PDF pixels/geometry and verify DeviceGray image color space,
source-color preservation, profile floors and failure on impossible byte limits.
All profiles have final-page cancellation checks. Workspace tests cover presets,
busy guards, selected identity, stale-result invalidation and exact comparison.

Natural sort is stable for equal names; reverse/rotate all/clear are guarded.
Existing input validation, HEIC/JPEG/PNG, EXIF, metadata stripping and protected
exports remain exercised. The UI contract is source-wiring validation, not AX.

## Real native UI

Packaged bundle opened two synthetic PNG files via Finder-style file events.
Application preset, Grayscale selection and preparation were activated via AX;
read-back showed 529,007-byte output under the 2 MB budget and two review panes.
Batch rotate changed both rows to 90° and cleared stale output. Clear presents
an explicit confirmation sheet describing original-file preservation.
Screenshots inspected at 1120 px and 950 px window widths: no visible clipping,
export controls reachable, original-color and grayscale pages clearly distinct.
Only synthetic sample documents appear in the published screenshot.

The review checkbox and Save a copy action opened the native save panel; it
no GUI file write was verified. The actual export bytes and exclusive
file-creation behavior are verified by automated core tests, not a GUI save.

## Size and performance

Packaged binary: 1,088,448 bytes. Bundle files: 1,532,774 bytes.
ZIP: 667,989 bytes. Packaging enforces <2 MB binary, <3 MB bundle, <1.5 MB ZIP
(decimal bytes); excludes system frameworks, Swift toolchain and filesystem overhead.
Source build has no third-party package downloads, but Xcode/Swift installation
itself is large and is not included in these budgets.

Parent-run release checks plus 12 repeated 20-page synthetic 1200×1600 batches:
5.70 seconds elapsed; maximum RSS 242,352,128 bytes, Apple M4 / macOS 27.0.
This is not a worst-case input benchmark or GUI memory measurement.

## Limits

Apple Silicon, macOS 14+. Ad-hoc signed, not notarized or sandboxed.
Optional local SDK search-path linker warnings remain; Swift compiler checks pass.
The older leak-tool caveat in PERFORMANCE.md remains; this release makes no
leak-free claim. No OCR, searchable-text/accessibility conversion or PDF input.
