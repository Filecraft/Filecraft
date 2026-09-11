# Changelog

All notable changes are recorded here. Prepare uses semantic versions while
remaining pre-1.0: file-format and API compatibility are not yet guaranteed.

## 0.7.0-beta.1

- Real PDF page operations share one local browser/Node adapter: merge, extract,
  reorder, duplicate and rotate; text/vector pages are copied rather than rasterized.
- Separate offline PDF Workbench with disposable worker jobs, cancellation,
  source-preserving exports, strict profiles, page history and output reparse.
- PDF CLI writes exclusively to a new path and bounds input/process work.
- Vendored pdf-lib keeps its MIT attribution; original code stays Hippocratic.
- Image Portable adds detailed measured/expected readiness explanations and a
  chained source-lineage regression. Native stable versions remain unchanged.
- CI actions are SHA-pinned and migrated to Node24 runtime implementations.
- PDF tools remain beta: no forms, signatures, annotations, encryption, OCR,
  sanitization or compression guarantee; full conformance/visual checks unknown.

## 0.6.0-beta.1

- Dependency-free shared readiness engine and source inspector CLI.
- Strict offline requirement profiles, tri-state evidence, reversible model
  operations, Portable undo/redo and light/dark presentation.
- Header-only inspection and model-only CLI workflows are explicitly scoped.
- Native Mac and Android releases remain at 0.5.0.

## 0.5.0

- Mac: explicit 150/200/300 DPI ceilings, identity-safe duplicate and move-last
  actions, expanded rendered regression checks. Apple Silicon, macOS 14+.
- Portable: arbitrary 36–600 DPI ceilings; per-page duplicate, rotate and remove;
  opt-in near-white threshold cleanup (not AI segmentation). JPEG/PNG browser
  companion for Windows/Linux/macOS, not native EXE/ELF packages.
- Android: framework-only experimental source and unsigned developer APK build;
  no network permission, no bundled runtime. Not an installable consumer release
  or store submission. See android/VERIFICATION.md for actual test coverage.
- Published 100-capability architecture backlog, first-person governance, store
  submission foundations and redesigned platform-aware website.
- Privacy remains local; no OCR, encryption, PDF input or forensic-erasure claim.

## 0.4.0 — 2026-09-11

### Added

- Balanced, Small File and true Grayscale compression profiles.
- Portal 500 KB, Application 2 MB/A4 and Photo 10 MB presets.
- Natural filename sort, reverse order, rotate all and confirmed clear.
- Resizable native settings sidebar and dedicated review workbench.
- Tested Workspace module separating UI from workflow coordination.
- Rendered grayscale/DeviceGray, profile floor, preset and batch regressions.
- Dependency-free editorial-green website with interactive preset guide,
  reduced-motion support and real v0.4 app imagery.
- Enforced size budgets: binary <2 MB, app files <3 MB, release ZIP <1.5 MB.

### Distribution

Apple Silicon ZIP: 667,989 bytes; app files: 1,532,774 bytes. System frameworks
and Swift/Xcode toolchain are not included. Retains macOS 14 minimum,
local-only processing and Hippocratic License 3.0 core. Ad-hoc signed,
not notarized. Existing canonical Pages URL retained after handle research.

## 0.3.0 — 2026-09-11

First public release; Hippocratic License 3.0 core.

### Added

- Per-page clockwise rotation in quarter turns, applied after EXIF orientation.
- Image-aspect, A4 and US Letter paper layouts with custom margins in points.
- Original-versus-output comparison and explicit selected-page navigation.
- Rendered-pixel regression checks for rotation, layout and margins.
- Original app icon, complete license/notice resources in the app bundle.
- Finder Open With and multi-file launch handoff into a single workspace.
- Responsive, script-free GitHub Pages website, contributor guide, code of
  conduct, security policy, issue forms and pull-request checklist.
- macOS CI for debug/release checks, strict compilation and packaging.

### Preserved

- Ordered multi-image PDF creation and drag-and-drop page reordering.
- Finished-PDF byte-budget enforcement and bounded encoding attempts.
- Progress, cancellation, explicit visual-review acknowledgment and
  exclusive new-file export that protects originals.
- Strictly local processing with no runtime dependencies or networking.

### Distribution notes

Apple Silicon, macOS 14+. Ad-hoc signed; not Developer ID signed or notarized.
Not sandboxed. Raster PDF output is lossy and requires visual review.

## 0.2.0 — unpublished local prototype

Native image-to-PDF feasibility build with size constraints, mixed JPEG/PNG/HEIC
inputs, EXIF orientation, metadata stripping, drag reordering, progress,
cancellation, overwrite protection and local packaging. Never a public release.
