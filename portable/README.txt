Prepare Portable 0.7.0-beta.1; Goni Sulaiman

QUICK START
Extract the whole ZIP. Open Prepare-Portable/index.html in a current desktop
Chrome, Edge or Firefox browser on Windows, Linux or macOS. Keep the files
together. No installation, local server, Node, Python or internet is needed.
Use the native Prepare.app on Apple Silicon macOS 14+ for PDFKit review and HEIC.
This companion is not a Windows EXE or Linux ELF binary. It uses your existing
browser, which is a separate prerequisite and not included in the size budget.

Add JPEG/PNG images, choose a preset, sort/reorder/rotate or split a spread,
set paper/margins/custom 36–600 DPI ceiling (0 = automatic) and a byte limit,
then Filecraft PDF. Optional near-white cleanup turns pixels above a threshold
white; it is not semantic background removal and may erase faint content.
Duplicate, rotate or remove individual pages before preparing. Split divides
the EXIF-oriented source into left then right halves before user rotation.
Review every page and check the legibility box to unlock Save PDF copy.
The browser controls where the copy is saved; use a new filename.

READINESS BETA
The shared engine powers page reorder/rotate/duplicate/remove undo and redo,
plus offline JSON requirement profile import/export. Importing images, splitting
a spread, removing the final page or clearing starts a new history. No autosave.
Checks distinguish pass, fail and unknown. Full PDF structural validation is
not available in this browser bundle, so overall readiness remains UNKNOWN
unless a known requirement fails. A small file is not proof of readability.
Imported profiles do not silently change export settings or prevent a knowingly
noncompliant save. Review the rule results. All files remain local.

PRIVACY / LIMITS
Everything runs in this page on your computer. No analytics, network requests,
accounts, server, external fonts, persistence or automatic updates. The page
blocks network connections with CSP. Browser extensions, sync folders and OS
swap/crash handling are outside Prepare's control. A trusted browser matters.
Originals are read only, not modified. Canvas re-encoding discards source EXIF
and GPS metadata; visible private content remains. Output is lossy raster PDF,
not OCR or searchable text. Preview shows embedded JPEGs in page geometry,
not an independent full PDF renderer. Check the PDF in a reader before use.

20 pages; 20 MB per image; 100 MB selected input; 24 megapixels per image.
Serial processing, three attempts; no unlimited compression below the floor.
A DPI ceiling can intentionally reduce pixels below a profile's automatic
edge limit; source resolution is never increased. Browser decoding can use a
full source bitmap; these caps are not a browser-memory guarantee. Cancel takes
effect between decode/encode operations. Animated PNG, HEIC, SVG, PDF input and
mobile browsers are not supported by this companion. Grayscale uses equal RGB
channels, unlike the Mac app's dedicated DeviceGray encoding.

SOURCE / LICENSE
https://github.com/Filecraft/Filecraft
https://filecraft.github.io/
Current original source: Apache-2.0, included as LICENSE. NOTICE contains
attribution. Historical 0.5 downloads retain their original Hippocratic terms.
Development tests use dependencies, but none are in this release folder.
I maintain Prepare independently. Read CONTRIBUTING.md and CODE_OF_CONDUCT.md
in the repository before joining in; report security problems privately at
https://github.com/Filecraft/Filecraft/security/advisories/new
