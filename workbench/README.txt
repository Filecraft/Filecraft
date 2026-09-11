Filecraft Workspace 0.10.0-beta.1

START
Extract this entire folder. Open index.html in a current desktop Chrome,
Edge or Firefox browser. Do not open the ZIP preview. No server, Node,
installation, account or network connection is required for this workbench.
If your organization blocks Blob workers, use the separately distributed
Node PDF CLI instead. JavaScript is required for document processing.

WORKFLOW
1. Add ordinary PDF files (or drag them onto the page).
2. Arrange the numbered source pages using Up/Down, Rotate, Duplicate,
   Remove and Reverse. Undo/Redo retain up to 32 page changes.
3. Set a byte ceiling and page limit, or import a version-1 JSON profile
   compatible with Prepare's shared readiness engine.
4. Create PDF copy. The output is parsed again and page geometry checked.
5. Read the checks. UNKNOWN is not PASS. Acknowledge the review requirement,
   save under a NEW name, then open the saved PDF in a trusted PDF reader
   and inspect EVERY page before submission.

RECEIPTS
Save receipt downloads optional unsigned JSON with output SHA-256 and byte count.
Verify a saved copy compares those bytes; it does not authenticate the receipt,
rerun transformations, certify a portal requirement or prove visual quality.
Editing the plan or requirements invalidates the old output and receipt.

EXTRACT / MERGE / SPLIT
Remove unwanted pages to extract a subset. Add more source files to merge.
To split into multiple files: export one subset, undo removals, select a
second subset, and save under a different name. This is not an automatic
multi-file splitter. Import and Clear reset history, and Clear asks first.
No autosave or session recovery: closing the tab discards the workspace.

LIMITS
10 files; 20,000,000 bytes each; 50,000,000 total input bytes; 100 pages.
Each parser/transform job has a 30-second deadline in a disposable worker.
Cancel terminates it. These guards do NOT provide a hard browser-memory cap.
Complex compressed resources can exhaust browser memory. Use trusted PDFs.

No encrypted PDFs, forms, signatures, annotations or active document features.
No PDF renderer/thumbnails in this workbench. The list shows source page
numbers and measured dimensions; review actual content in your PDF reader.
No OCR, password removal, raster optimization or compression guarantee.
Copied text/vector pages are not rasterized. Document-level outlines and
metadata may be lost. This is NOT a sanitizer: embedded resources and visible
private details may survive. No PDF/A, accessibility or institutional
certification is claimed. Parsing and geometry checks do not prove full
structural correctness or visual fidelity. Readiness remains UNKNOWN when
required evidence is unverified. An impossible size ceiling produces no copy.

PRIVACY / ORIGINALS
No document upload, analytics, fonts, remote scripts or accounts. Runtime
network connections are blocked by Content Security Policy. Browser
extensions and OS/file providers are outside this guarantee. Use local,
non-synced files and a trusted browser. Original inputs are never written.
The browser controls downloads and overwrite prompts: choose a new name.

LICENSE / DEPENDENCIES
Current original Prepare code: Apache-2.0. See LICENSE and NOTICE.
Historical releases through 0.8 retain their original Hippocratic terms.
Bundled pdf-lib: separately MIT licensed. See THIRD-PARTY.txt and
vendor/LICENSE and the other vendor/LICENSE.* files. No dependency download happens at runtime.

Help: https://filecraft.github.io/getting-started/
Source: https://github.com/Filecraft/Filecraft
