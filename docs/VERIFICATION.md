# Verification

Current release: [v0.4.0 verification](VERIFICATION-0.4.md).
The evidence below is retained for the v0.3.0 release. scope

The 0.3.0 release is validated with executable core checks, release packaging,
synthetic-image UI smoke testing and browser checks of the project website.
This is not a professional security audit or full accessibility certification.

## Website

- Dependency-free HTML/CSS. No JavaScript, remote fonts, analytics or forms.
- Browser DOM layout checked at 1440, 768, 390 and 320 pixels wide: no
  horizontal document overflow or out-of-viewport element rectangles.
- Install anchor navigation and native FAQ expansion checked in a browser.
- Desktop and mobile screenshots inspected for readable layout and clipping.
- Automated offline check validates local assets, unique anchors, external
  HTTPS URLs, heading count, alt attributes, versioned download links,
  visible notarization/license disclosures, focus and reduced-motion styles.
- Website is served by GitHub Pages, subject to GitHub's request logging.

## App

See [performance and core checks](PERFORMANCE.md),
[architecture](ARCHITECTURE.md) and [security scope](../SECURITY.md).

## Packaged app smoke test

Verified against the arm64 0.3.0 app using macOS Accessibility APIs:

- Multi-file Finder/Open With launch imports both synthetic sample PNGs into
  one workspace (a failed earlier WindowGroup routing experiment was fixed).
- A4 selection, per-page 90° rotation and moving page 2 before page 1.
- Preparing two pages produced a reopened preview: 579,035 bytes under a 2 MB
  limit for that sample/settings run. This is not a general compression claim.
- Page navigation showed two single-page PDF panes for the same selected page.
- Rotation after preparation cleared output and review approval.
- Review checkbox gates saving; an attempted existing destination was rejected.
- Core save tests separately verify new-file export bytes and original protection.
- Screenshot captured from the real packaged app with synthetic samples only.
- The full comparison is visible at 1200×740; minimum window is 850×620 with
  a scrolling control column. Not a complete VoiceOver or keyboard audit.

The UI and generated PDF do not add OCR. macOS PDFKit may independently expose
Live Text in its view; that is platform behavior, not a searchable output promise.
