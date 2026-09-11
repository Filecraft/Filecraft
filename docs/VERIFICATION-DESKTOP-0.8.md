# Desktop 0.8.0-beta.1 verification

Release source: `5befffb63e5234e569e5b94657fdf93079190b80`.

- 48 local desktop tests passed, including real Tesseract OCR, form-widget pixels,
  PDF geometry/passwords, native UI exports/previews, XML validation and document order.
- Independent reviews found and then verified fixes for form rendering, PDF text
  wrapping, XML controls and reading order. Final wrapping review also ran 3,000
  seeded fuzz cases. This does not certify arbitrary hostile files.
- Desktop CI run 34642679236 passed Ubuntu 24.04 x64, Windows 2022 x64,
  macOS 15 ARM64 and macOS 15 Intel. Each exercised its frozen executable.
  OCR/media engine-dependent tests run on Linux; unavailable optional engines
  are explicitly skipped elsewhere. Local macOS OCR/media tests passed.
- Existing native checks run 34642679235 and browser checks run 34642679214 passed.
- Downloaded Intel/ARM64 archives passed real frozen PDF/image/archive operations,
  AES-256, preview and rasterization on the local Mac (Intel through Rosetta).
  Both executable signatures verified; neither package is notarized.
- Four published ZIPs and their SHA-256 files were downloaded/stream-verified
  against CI artifacts. ZIP integrity checks passed.
- Static site checks cover 40 canonical pages; 80 viewport/theme/no-JavaScript
  product-page cases passed locally.
- Pinned Python runtime requirements audit reported no known vulnerabilities;
  this is not a security guarantee or complete legal compliance certification.

## Download sizes

| Platform | ZIP bytes |
|---|---:|
| macOS ARM64 | 28440126 |
| macOS Intel | 29856556 |
| Windows x64 | 32642312 |
| Linux x64 | 50435866 |

Intel cryptography is statically linked to avoid a collision with Python's bundled
OpenSSL. An optional legacy-provider warning may appear; tested AES-256 works.
Legacy encrypted PDFs unsupported by the available crypto provider may be rejected.

## Remaining boundaries

See [desktop scope](../desktop/README.md): not universal format conversion, not
layout-faithful Office conversion, no general PDF content editor, no hostile-file
sandbox, no guaranteed compression savings. OCR/FFmpeg require separately installed
local engines. Windows is unsigned; Mac builds are not notarized. Existing mobile
releases remain separate; no new store signing or mobile parity is claimed.
