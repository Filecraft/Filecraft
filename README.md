<div align="center">
  <img src="docs/assets/icon.svg" width="96" height="96" alt="Prepare icon">
  <h1>Prepare</h1>
  <p><strong>A smaller file. A simpler handoff.</strong></p>
  <p>Scans and photos → a size-constrained PDF. Entirely on your Mac.</p>
  <p>
    <a href="https://gonisulaimann.github.io/Prepare/">Website</a> ·
    <a href="https://github.com/gonisulaimann/Prepare/releases/latest">Download</a> ·
    <a href="CONTRIBUTING.md">Contribute</a>
  </p>
  <p>
    <a href="https://github.com/gonisulaimann/Prepare/actions/workflows/ci.yml"><img src="https://github.com/gonisulaimann/Prepare/actions/workflows/ci.yml/badge.svg" alt="macOS checks"></a>
    <img src="https://img.shields.io/badge/macOS-14%2B-183e33" alt="macOS 14 or newer">
    <img src="https://img.shields.io/badge/Swift-6-183e33" alt="Swift 6">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Hippocratic_3.0_core-657b58" alt="Hippocratic License 3.0 core"></a>
  </p>
</div>

An application portal says “2 MB maximum.” Your scans say otherwise.
Prepare turns up to 20 images into one ordered, reviewed PDF under your chosen
byte limit—or tells you when it cannot fit within its quality floor.

No account. No uploads. No analytics. No subscription. No AI service.
Just native SwiftUI, ImageIO, CoreGraphics and PDFKit, with no package dependencies.

![Prepare showing native page controls and source-versus-PDF review](docs/assets/screenshot.png)

## What makes it useful

- **A real byte budget.** Set 0.01–100 decimal MB. The finished PDF, not a size
  estimate, must fit before Prepare offers it for export.
- **Useful starting points.** Portal 500 KB, Application 2 MB with A4/24 pt
  margins, and Photo 10 MB. All remain editable.
- **Three compression profiles.** Balanced, Small File and true Grayscale.
  Source comparison retains original color.
- **Batch controls.** Natural filename sort, reverse order, rotate all and
  confirmed clear, without losing the selected page.
- **Pages in your order.** Drag to reorder or use move buttons. Rotate each
  page in 90° steps after the image's EXIF orientation is applied.
- **Paper that suits the handoff.** Image-aspect, A4 and US Letter layouts,
  with custom margins in points. Aspect-fit content, not accidental cropping.
- **Review before you send.** Page-by-page source-versus-output comparison.
  The source preview is downsampled; the output is the actual generated PDF.
- **Originals stay original.** Save a separate copy. Existing destination
  files are rejected, including the source images.
- **Metadata stays behind.** Source metadata dictionaries, including EXIF/GPS,
  are not copied. Transparency is flattened onto white.
- **Bounded work.** Serial image buffers, bounded decode sizes, at most five encoding
  attempts, progress reporting and cooperative cancellation.

This is intentionally a focused image-to-PDF utility, not a general PDF editor.

## Windows and Linux: Portable preview

[Download the offline Portable preview](https://github.com/gonisulaimann/Prepare/releases/tag/v0.5.0-portable-preview.1).
Extract the whole ZIP and open `Prepare-Portable/index.html` in a current desktop
Chrome, Edge or Firefox browser. No server or internet needed after download.
This is a 16,642-byte browser companion, not a native Windows/Linux binary.
The stable Mac app below remains v0.4.0.

Portable supports JPEG/PNG, compression profiles, DPI ceilings, margins, page
ordering and left/right spread splitting. Windows/Linux Chromium and Firefox
[CI checks passed](https://github.com/gonisulaimann/Prepare/actions/runs/34558322793).
Read the preview release notes for input, browser, privacy and export limitations.
[Portable source at its tested tag](https://github.com/gonisulaimann/Prepare/tree/v0.5.0-portable-preview.1/portable).

## Download and install

[Download Prepare 0.4.0 for Apple Silicon](https://github.com/gonisulaimann/Prepare/releases/download/v0.4.0/Prepare-0.4.0-arm64.zip)

Requires macOS 14 or later. Expand the ZIP and drag `Prepare.app` to Applications.
Intel and universal release binaries are not provided or release-tested.

> **Signing:** this release is ad-hoc signed, **not Developer ID signed or
> notarized**, and not sandboxed. macOS may block first launch. Review the
> source and checksum before deciding whether to approve it under System
> Settings → Privacy & Security after attempting to open it. Do not disable
> Gatekeeper globally. Managed Macs may disallow this build.

Verify a download in the directory containing both release assets:

```sh
shasum -a 256 -c Prepare-0.4.0-arm64.zip.sha256
```

The checksum detects accidental corruption; it is not an independent publisher
identity proof. You can build locally instead. No Developer ID certificate is
needed for a local ad-hoc build.

Downloading and using Prepare is subject to the [Hippocratic License 3.0 core](LICENSE).

## How to use

1. Add or drop JPEG, PNG or HEIC still images, or use Finder **Open With → Prepare**.
2. Pick a workflow preset or customize the compression profile, byte limit,
   paper and margins. Arrange pages individually or use batch actions.
3. Enter your maximum PDF size and choose **Prepare PDF**.
4. Inspect each output page, using comparison mode when useful. Changing any
   layout, order or compression setting invalidates the previous result.
5. Acknowledge that you reviewed the output, then save to a new filename.

MB means 1,000,000 bytes. “Original” page size means the image's aspect ratio
with a maximum 10-inch page edge, not its embedded DPI or original physical
size. A4 and US Letter use portrait paper. Margins are points (72 per inch).

Keyboard shortcuts: ⌘O add images, ⌘R prepare, ⌘[ / ⌘] previous/next page,
⇧⌘S save a copy, Escape cancel active preparation.

## Honest limits

| Boundary | Behavior |
| --- | --- |
| Inputs | 1–20 single-frame JPEG, PNG or HEIC images |
| Per-file limit | 40 MB, 80 megapixels, at most 20,000 px per dimension |
| Existing PDFs / animation | Rejected; never silently rasterized or truncated |
| Compression | Lossy JPEG and possible downsampling; legibility is not guaranteed |
| Impossible budget | Explicit failure, never an oversized “success” |
| Source comparison | Downsampled preview, not a pixel-identical quality measurement |
| Output | Raster PDF, without OCR text or tagged accessibility structure |
| Cancellation | Between image operations; cannot interrupt Apple's codec mid-call |
| Privacy | Visible personal data and standard PDF producer/date metadata may remain |

The app has no networking code. Files selected from a syncing folder can still
sync through that provider. Prepare is not an anonymizer, redaction tool or
secure-erasure utility. Read the complete [security and privacy policy](SECURITY.md).

The v0.4.0 Apple Silicon ZIP is **668 KB** (667,989 bytes); the installed app
files total **1.53 MB**. System frameworks and the Swift toolchain are excluded.
See [v0.4 verification](docs/VERIFICATION-0.4.md) and
[domain findings](docs/DOMAIN.md).

## Build from source

Requires macOS 14+ and Swift 6 (Xcode command-line tools). No third-party Swift
packages, cloud credentials or web build tools are needed for the app. Apple’s
Swift toolchain is a separate, much larger download if it is not installed.
Use the shallow clone below to avoid downloading release history.

```sh
git clone --depth 1 https://github.com/gonisulaimann/Prepare.git
cd Prepare
swift run Prepare
```

Build the distributable bundle and checksum:

```sh
bash scripts/package.sh
open build/Prepare.app
```

Outputs: `build/Prepare.app`, `build/Prepare-0.4.0-arm64.zip` and its `.sha256`
(on an Apple Silicon build host). The package includes the full license,
notice and original app icon. Packaging uses an ad-hoc signature by default.

## Test

```sh
swift run PrepareChecks --ui-contract
swift run -c release PrepareChecks --ui-contract
swift build -c release -Xswiftc -warnings-as-errors
swift run -c release PrepareChecks --stress
python3 scripts/check-site.py
node scripts/test-site.cjs
python3 scripts/test_release_budget.py
```

`PrepareChecks` is an executable integration harness, not an XCTest target.
It generates synthetic images locally and checks actual PDF bytes, reopened
pages, rendered pixels, input rejection, original-file protection, metadata
stripping and cancellation. `--stress` exercises repeated 20-page batches.

See [verification results](docs/VERIFICATION.md) for the measured release run
and its hardware/workload limits. There are no unsupported “instant” or
universal performance promises here.

## Project map

```text
Sources/Prepare/        SwiftUI workspace and PDFKit review
Sources/PrepareCore/    Validation, ordering, presets, profiles and bounded PDF encoding
Sources/PrepareWorkspace/ Testable main-actor state and bounded preview coordination
Sources/PrepareChecks/ Synthetic integration and regression checks
scripts/               App packaging, icon generation and website checks
docs/                  Dependency-free GitHub Pages website and technical docs
.github/               macOS CI, issue forms and pull-request checklist
```

[Architecture](docs/ARCHITECTURE.md) · [Release checklist](docs/RELEASING.md) ·
[Changelog](CHANGELOG.md) · [Acknowledgments](docs/ACKNOWLEDGMENTS.md)

## Contribute

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Focused fixes, accessibility
feedback and testing on supported Macs are especially useful. Keep everything
local. Use synthetic samples in issues. Substantial AI assistance should be
disclosed; contributors remain responsible for understanding and verifying
all submitted code.

Maintained by [Goni Sulaiman](https://github.com/gonisulaimann). Participation
follows our [code of conduct](CODE_OF_CONDUCT.md). Please use
[private vulnerability reporting](https://github.com/gonisulaimann/Prepare/security/advisories/new)
for security issues.

## License

Copyright © 2026 Goni Sulaiman and Prepare contributors.

**Hippocratic License 3.0, core configuration, no optional modules.** Read
[LICENSE](LICENSE) and [NOTICE](NOTICE). This is ethical-source,
source-available software: the license restricts harmful uses and is **not
an OSI-approved open-source license**. The first public release replaces the
unpublished prototype's MIT notice at the project owner's direction.
