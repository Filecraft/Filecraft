# Filecraft Desktop 0.10.0-beta.1 (development)

A larger, offline desktop suite alongside the tiny image app and browser tools.
Native Tk controls, a separate process for conversion/rendering, no HTTP server,
no accounts, no uploads, and no runtime downloads. Original files are never
replaced. Save into local folders: OS file providers can sync independently.

## Start

Extract the complete archive before launching Filecraft-Desktop (Windows:
Filecraft-Desktop.exe). Keep the _internal directory beside the executable.
Linux: mark Filecraft-Desktop executable if your extractor lost permissions, then
run it on a desktop with X11/XWayland. macOS: this beta is not notarized. Do not
disable Gatekeeper; inspect/build the source if policy blocks the download.
Windows builds are unsigned and may trigger reputation warnings.

Source qualification: Python 3.13 with Tk, `pip install -r desktop/requirements.txt`, then
`python desktop/launch.py`. Development packaging also needs PyInstaller 6.22.2.
Original Filecraft work now uses Apache-2.0; earlier published binaries retain
their original licenses. Dependencies remain separately licensed; preserve the
complete bundled `licenses/` directory, including PREPARE-NOTICE. See
[licensing scope](../docs/LICENSING.md) and [dependencies](../docs/DEPENDENCIES.md).
New packages retain Vera fonts and their Bitstream license, exclude unused
DarkGarden fonts, and collect exact-version OpenSSL notices on every platform.
Packaging requires network access for upstream legal texts (not at runtime);
unknown TLS versions or missing texts block publication. This is not a complete
recursive native-library audit.

## Use

Choose a local file, choose a target in the dropdown, select options and export
a NEW filename. Preview source/output PDFs or images with the page/frame control.
PDF page selection is comma-separated, 1-based; rotation is added clockwise.
Inspect PDF shows form field names; fill values are a JSON object. Passwords
travel to the worker over stdin, not process arguments or saved preferences.

The format registry lists plausible conversions; malformed/unsupported variants
are rejected. It does NOT claim every extension can become every other format.

- Any extension: lossless ZIP or GZ archive compression. This wraps bytes; it is
  not semantic conversion. Already compressed files can grow. No extraction UI.
- Images: PNG, JPEG, WebP, TIFF, BMP, GIF, ICO, PPM/PGM/PBM/PNM, PCX, TGA, DDS,
  ICNS, JPEG2000 and AVIF through bundled Pillow codecs. Targets: PNG, JPEG,
  WebP, TIFF, BMP, GIF, ICO, PPM or image PDF. One chosen frame only; animation,
  metadata, profiles and transparency may be lost. Not camera RAW/PSD/SVG support.
- UTF-8 text/Markdown/CSV/TSV/JSON/XML/HTML/log/YAML/INI/TOML/RST: TXT, MD, safe
  escaped HTML, DOCX or PDF. Text-first, not a layout-preserving Office engine.
- DOCX/ODT/PPTX/ODP/XLSX/ODS/EPUB: bounded text extraction to those same targets.
  Images/layout/macros are discarded. Spreadsheet extraction is NOT cell-faithful
  conversion; formulas/styles and empty-cell positions are not reconstructed. Cached values and shared strings are extracted.
- Audio/video: with separately installed local FFmpeg on PATH, WAV, FLAC, MP3,
  OGG/Opus, AIFF, AAC, M4A, MP4, MOV, MKV, WebM and AVI to supported audio/video
  outputs. Codec availability depends on FFmpeg. Pipe-only inputs deliberately
  reject files requiring seek access. Playlists and network protocols disabled.
- PDF: local visual preview, page operations, text/image export, lossless stream
  optimization, explicitly lossy rasterization, password handling, form filling,
  annotations and OCR. Ordinary AcroForm widgets are rendered without JavaScript
  or document action callbacks; XFA visual rendering is rejected. Previews identify
  the filename, page and input SHA-256 and clear after export.

OCR requires separately installed Tesseract and its language data. Media requires
separately installed FFmpeg. Prepare detects but never installs or downloads them.
These are real local engines, not cloud fallbacks. All other listed conversions
are bundled. Additional engines retain their own licenses.

## Requirements, receipts and CLI

Maximum decimal MB and page limits are optional; blank means no limit. A shared
version-1 JSON profile may also constrain formats, dimensions, orientation and
filenames. The output is measured before publication; failed requirements leave
no output copy. Unknown properties remain NEEDS_REVIEW, never a pass. The receipt
stores only mechanical checks—not visual/accessibility/full-conformance proof.

Save receipt after export writes a separate JSON file exclusively. It contains
hashes, sizes and your chosen rules, not full source paths/passwords. Profile IDs
and descriptions are user-entered and may themselves contain private details.

CLI: `Filecraft-Desktop prepare input.png --target pdf --output prepared.pdf
--max-bytes 2000000` (one command line). `--cli` before the command is also
accepted. JSON output includes `result.receipt`; save that object as receipt.json
and run `Filecraft-Desktop verify prepared.pdf --receipt receipt.json`. Match returns
0; mismatch 2; processing error 1. The receipt is unsigned/editable: byte identity
is not authenticity or institutional acceptance. `formats input.png` lists actual
available targets. CLI uses the same bounded separate worker as the UI.

## Boundaries

100 MiB input/output, 100 PDF pages, 20 million pixels per image, 2 MB text,
20 MB expanded Office XML, 180-second worker deadline. Some library allocations
are not fully contained on macOS/Windows. Process isolation is not an OS security
sandbox. Don't use this beta as a hostile-file sanitizer. Copying PDFs may retain
active content; no operation guarantees removal of all threats. OCR is fallible;
review text. Rasterization destroys original text, signatures and interactivity.
No arbitrary PDF content editor, general annotation editor or signature authority.
No compression size guarantee. Originals remain the authoritative fallback.

Exports use atomic exclusive hard-link publication, requiring a local filesystem
that supports hard links (e.g. NTFS/APFS/ext4). FAT/exFAT destinations may fail;
save locally and copy the result manually. Cancellation can race with completed
publication; the UI tells you to check for a newly created copy. Worker temporary
files may remain after forced cancellation; they are local, not uploaded.

Mobile store distribution and Apple notarization are not provided by this beta.
The existing Android developer experiment and browser packages remain separate.
