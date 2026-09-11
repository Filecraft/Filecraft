# Security and privacy

## Report a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/gonisulaimann/Prepare/security/advisories/new).
Include affected version, reproduction steps and a minimal synthetic sample.
Do not file a public issue or upload a confidential document. This is a small,
volunteer-maintained project; no response-time or bounty promise is made.
Only the latest release is currently supported.

## Local by design

The Prepare application has no networking code, analytics, accounts, AI calls,
automatic updater, clipboard monitor or third-party packages. It works
without a network connection. The project website and release downloads are
hosted by GitHub and subject to GitHub's own network logging; they are separate
from the app. “Local” does not mean files selected from iCloud Drive stop
syncing: choose local folders if that distinction matters to you.

The published app is **ad-hoc signed, not Developer ID signed or notarized**,
and **not sandboxed**. It requests no Full Disk Access, Accessibility or Input
Monitoring permissions. A signature integrity check is not Apple approval.

## Threat model and boundaries

- ImageIO, CoreGraphics and PDFKit decode user-selected files. Use a supported,
  patched macOS version; malicious image decoding remains an attack surface.
- Inputs are capped at 20 single-frame JPEG/PNG/HEIC images, 40 MB and 80
  megapixels each, and 20,000 pixels per dimension. Animated images and
  arbitrary existing PDFs are rejected, not silently flattened.
- Encoding has five bounded attempts and serial page buffers. Cancellation
  is cooperative between codec operations, not an immediate interruption of
  an Apple codec. A source changed by another program during a run is outside
  the immutable-input assumption; prepare again after any external edits.
- Source metadata dictionaries (including EXIF/GPS) are not copied. Pixels
  may still identify people or reveal information. Standard PDF producer/date
  metadata may remain. This is not an anonymizer or redaction tool.
- Output is a raster PDF, not OCR text or a tagged accessible document. JPEG
  encoding is lossy; visual review is required before export.
- Existing destination paths are rejected, including originals. A failed write
  can leave a partial newly created file; inspect errors and use a new name.
- The app does not persist projects or thumbnails deliberately. macOS may keep
  normal window, swap or recent-location state. This is not secure erasure.

The no-network policy is a reviewed implementation property, not an OS-enforced
sandbox guarantee. Please report any code path contradicting it.
