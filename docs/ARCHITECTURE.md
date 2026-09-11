# Architecture

```text
SwiftUI workspace (main actor)
  ordered pages + rotation + paper + margin + byte limit
                 │ immutable settings snapshot
                 ▼
Task.detached → PrepareCore
  validate → bounded ImageIO decode → white flatten → JPEG encode
  → rotated, aspect-fit page in CoreGraphics PDF
                 │ first complete PDF within byte budget
                 ▼
PDFKit review + downsampled source comparison → explicit review → new file
```

## Targets

- `PrepareCore`: Foundation, ImageIO, CoreGraphics and UniformTypeIdentifiers.
  Validation, page ordering, layout/rotation and bounded encoding. No UI.
- `Prepare`: SwiftUI/AppKit workspace, file panels and PDFKit preview. Image
  preparation runs off the main actor. UI edits invalidate reviewed output.
- `PrepareWorkspace`: testable main-actor state, preset application, busy guards,
  invalidation and bounded asynchronous preview requests.
- `PrepareChecks`: generated fixtures, rendered-pixel assertions, PDF round
  trips, input rejection, metadata checks, cancellation and overwrite guards.

## Size fitting

MB means 1,000,000 bytes. UI accepts 0.01–100 MB. Core accepts positive byte
limits up to 100,000,000. Balanced and Grayscale try five candidates in descending quality:

| Maximum image edge | JPEG quality |
| ---: | ---: |
| 2400 px | 0.85 |
| 2000 px | 0.75 |
| 1600 px | 0.65 |
| 1200 px | 0.55 |
| 960 px | 0.45 |

Small File uses only the last three rows, starting at 1600 px / 0.65.
Grayscale uses a DeviceGray canvas and embeds grayscale JPEG images; the
review source remains in original color. A Small File or Grayscale choice
is not a promise that every input becomes smaller than another profile.

The first complete PDF no larger than the target is returned. Otherwise the
engine reports that it cannot fit within its floor. This is a bounded search,
not a mathematically optimal compressor or a visual-quality guarantee.
Upsampling source detail cannot improve legibility. Review at a useful zoom.

Original paper mode means **image aspect ratio**, with a 720-point maximum
page edge, not the camera file's DPI or original physical dimensions. A4 and
US Letter are portrait pages with aspect-fit content; rotation changes image
orientation, not the chosen paper orientation. Margins are points (72/inch).
Transparency is flattened to white; source EXIF orientation is applied before
user rotation. Standard PDF metadata can remain.

## Invariants

1. The byte limit applies to the finished PDF, including its overhead.
2. The selected page order is the output order, even for repeated inputs.
3. Original files are never written; destination creation is exclusive.
4. Changing layout, order, rotation or budget clears the previous result.
5. Cancellation checks happen between expensive operations and before return.
6. Image buffers are page-scoped; no full-resolution multi-page image cache.
7. Source comparison is downsampled, not a pixel-identical quality oracle.
8. No user data leaves the application through application network code.

See [SECURITY.md](../SECURITY.md) for assumptions and limitations.
