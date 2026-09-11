# Next 100 capabilities

This is a prioritized architecture backlog, not a claim of 100 shipped features. No dates are promised. Implemented entries identify the actual platform; proposed entries require separate design, test and release gates. P0 denotes the current implemented slice; P1 is foundational, P2 follows after core reliability. Android delivery remains gated by real emulator/device results.

Runtime budget: Mac executable <2 MB/app files <3 MB/archive <1.5 MB; Portable expanded <200 KB/archive <100 KB; Android target APK <1 MB. Toolchains and development tests are not shipped. Memory: bounded image dimensions, serial decode, bounded retries/previews; measured peak RSS is workload-specific, not a worst-case guarantee.

Encryption is deferred until an audited implementation and license/size review exists. Near-white flattening is threshold whitening, not AI segmentation. Metadata stripping remains on; retention controls are proposed. Offline OCR/models are not bundled.

Machine-readable acceptance criteria: [features.json](../roadmap/features.json).

## Geometry

| ID | Feature | Priority | Status |
|---|---|---|---|
| F001 | Arbitrary DPI ceiling | P0 | portable-implemented |
| F002 | Native 150/200/300 DPI ceiling | P0 | mac-implemented |
| F003 | Per-page paper size | P1 | proposed |
| F004 | Per-page margins | P1 | proposed |
| F005 | Auto portrait/landscape selection | P1 | proposed |
| F006 | Manual crop rectangle | P1 | proposed |
| F007 | Perspective quadrilateral correction | P1 | proposed |
| F008 | Deskew angle estimation | P1 | proposed |
| F009 | Bleed/safe-area overlay | P1 | proposed |
| F010 | Two-up page imposition | P1 | proposed |

## Batch workflow

| ID | Feature | Priority | Status |
|---|---|---|---|
| F011 | Duplicate selected page | P0 | mac-portable-implemented |
| F012 | Move selected page to end | P0 | mac-implemented |
| F013 | Per-page removal | P0 | portable-implemented |
| F014 | Natural folder import | P2 | proposed |
| F015 | Multiple independent output jobs | P2 | proposed |
| F016 | Filename template expansion | P2 | proposed |
| F017 | Watch-folder queue | P2 | proposed |
| F018 | Drag-drop input zones | P2 | proposed |
| F019 | Saved local job presets | P2 | proposed |
| F020 | Command-line batch driver | P2 | proposed |

## Image cleanup

| ID | Feature | Priority | Status |
|---|---|---|---|
| F021 | Near-white threshold whitening | P0 | portable-implemented |
| F022 | Live threshold comparison | P2 | proposed |
| F023 | Manual white balance | P2 | proposed |
| F024 | Local contrast adjustment | P2 | proposed |
| F025 | Adaptive monochrome threshold | P2 | proposed |
| F026 | Denoising with bounded tile buffers | P2 | proposed |
| F027 | Shadow compensation | P2 | proposed |
| F028 | Background color picker | P2 | proposed |
| F029 | Border cleanup mask | P2 | proposed |
| F030 | Reversible per-page edit stack | P2 | proposed |

## Compression

| ID | Feature | Priority | Status |
|---|---|---|---|
| F031 | Per-page quality override | P2 | proposed |
| F032 | Text/photo-aware profile suggestion | P2 | proposed |
| F033 | Lossless PNG embedding for line art | P2 | proposed |
| F034 | JPEG pass-through when privacy-safe | P2 | proposed |
| F035 | Output byte contribution report | P2 | proposed |
| F036 | Optimize only largest page | P2 | proposed |
| F037 | Monochrome bilevel PDF encoding | P2 | proposed |
| F038 | Target-byte binary search | P2 | proposed |
| F039 | User quality-floor control | P2 | proposed |
| F040 | Embedded image deduplication | P2 | proposed |

## Privacy and security

| ID | Feature | Priority | Status |
|---|---|---|---|
| F041 | PDF password encryption via audited platform/library | P1 | proposed |
| F042 | Owner-permission controls with clear limitations | P1 | proposed |
| F043 | Optional document title and author | P1 | proposed |
| F044 | Metadata removal report | P1 | proposed |
| F045 | Explicit metadata retention opt-in | P1 | proposed |
| F046 | Redaction by raster destruction | P1 | proposed |
| F047 | Redaction preview warning | P1 | proposed |
| F048 | Private temporary-directory audit | P1 | proposed |
| F049 | No-network build permission regression | P1 | proposed |
| F050 | Dependency vulnerability inventory | P1 | proposed |

## Review and accessibility

| ID | Feature | Priority | Status |
|---|---|---|---|
| F051 | Keyboard shortcuts reference | P2 | proposed |
| F052 | Screen-reader page reorder announcements | P2 | proposed |
| F053 | High contrast native palette | P2 | proposed |
| F054 | Reduced-motion parity | P2 | proposed |
| F055 | Zoom-to-legibility region | P2 | proposed |
| F056 | Page-by-page before/after difference view | P2 | proposed |
| F057 | Printable proof sheet | P2 | proposed |
| F058 | Keyboard-only save confirmation | P2 | proposed |
| F059 | Localized error messages | P2 | proposed |
| F060 | RTL layout validation | P2 | proposed |

## Input and capture

| ID | Feature | Priority | Status |
|---|---|---|---|
| F061 | Android share-sheet image intake | P2 | proposed |
| F062 | Android camera capture through system intent | P2 | proposed |
| F063 | Clipboard image paste | P2 | proposed |
| F064 | HEIC portable format investigation | P2 | proposed |
| F065 | TIFF multipage input | P2 | proposed |
| F066 | WebP input validation | P2 | proposed |
| F067 | AVIF input validation | P2 | proposed |
| F068 | PDF input rasterization with explicit text loss | P2 | proposed |
| F069 | Local scanner import on macOS | P2 | proposed |
| F070 | Folder selection with file-count preflight | P2 | proposed |

## Output and interchange

| ID | Feature | Priority | Status |
|---|---|---|---|
| F071 | PDF/A investigation with independent validator | P2 | proposed |
| F072 | PDF bookmarks from filenames | P2 | proposed |
| F073 | Optional page-number stamps | P2 | proposed |
| F074 | Visible watermark overlay | P2 | proposed |
| F075 | Batch ZIP export | P2 | proposed |
| F076 | Split output by page count | P2 | proposed |
| F077 | Split output by byte limit | P2 | proposed |
| F078 | Sidecar job manifest export | P2 | proposed |
| F079 | Open output in system viewer | P2 | proposed |
| F080 | Android output share sheet | P2 | proposed |

## Platform delivery

| ID | Feature | Priority | Status |
|---|---|---|---|
| F081 | Android native SAF to PdfDocument workflow | P1 | proposed |
| F082 | Android process-death recovery policy | P1 | proposed |
| F083 | Android low-memory-device stress suite | P1 | proposed |
| F084 | Mac sandbox/security-scoped URL support | P1 | proposed |
| F085 | Mac Developer ID notarization | P1 | proposed |
| F086 | Windows native lightweight host feasibility | P1 | proposed |
| F087 | Microsoft Store packaging feasibility | P1 | proposed |
| F088 | Linux desktop launcher and package metadata | P1 | proposed |
| F089 | ARM Linux execution matrix | P1 | proposed |
| F090 | Offline update checksum verifier | P1 | proposed |

## Quality and community

| ID | Feature | Priority | Status |
|---|---|---|---|
| F091 | Public synthetic adversarial corpus | P1 | proposed |
| F092 | EXIF orientation eight-way golden fixtures | P1 | proposed |
| F093 | Unicode filename corpus | P1 | proposed |
| F094 | Fuzz PNG/JPEG header parsers | P1 | proposed |
| F095 | Property-based layout checks | P1 | proposed |
| F096 | Cancellation race injection | P1 | proposed |
| F097 | Long-run repeated-session memory baseline | P1 | proposed |
| F098 | Reproducible archive provenance | P1 | proposed |
| F099 | Translation contribution pipeline | P1 | proposed |
| F100 | Cross-platform feature parity dashboard | P1 | proposed |
