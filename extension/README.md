# Filecraft browser workspace

A full local workspace beside your application tab, not an upload interceptor.
Choose PDF files explicitly, set your own size/page requirements, merge, reorder,
extract or rotate pages, undo changes, prepare a copy, acknowledge visual review,
and save the output plus an optional SHA-256 receipt. Verify a later copy against
that receipt. No host permissions, content scripts, download monitoring,
remote code, telemetry, native messaging, accounts or uploads.

## Development installation (not marketplace publication)

- Chromium/Chrome/Edge: extract the Chromium ZIP, open the browser's extension
  management page, enable developer mode and load the extracted folder.
- Firefox: temporary development load through about:debugging → This Firefox →
  Load Temporary Add-on → manifest.json. Release Firefox requires Mozilla signing
  for permanent installation. Temporary add-ons disappear on restart.
- Safari: not yet packaged or qualified. The web workspace is not a Safari
  extension. Xcode's Safari web-extension converter, a containing app, signing
  identity and distribution qualification are required.

Toolbar action opens workspace/index.html. Files stay in that tab's memory;
closing it discards the session. Save copies before closing. Browser download
location/overwrite prompts and browser/OS sync are outside Filecraft’s control.
Use local non-synced folders for sensitive work. No automatic updates outside
normal browser store/update behavior when a signed store version exists.

10 PDFs, 20 MB each, 50 MB total, 100 pages, 30-second worker deadline. Ordinary
unencrypted PDFs only. Forms, signatures and annotations are rejected. The
browser workspace does not OCR, raster-compress, sanitize, repair or prove PDF/A,
accessibility, authenticity or portal acceptance. Desktop has broader adapters.
A receipt is unsigned and editable; it proves matching bytes, not document truth.
Receipt profiles may disclose personal requirements; review before sharing.

## Build / qualification

    python3 scripts/package_workbench.py --sync
    python3 extension/package.py
    python3 -m unittest discover -s extension/tests -v
    node extension/tests/browser.cjs

Packaging is deterministic. The real extension workflow test must pass before a
browser is called qualified. See store/README.md for publication boundaries.
Original current source is Apache-2.0 after the prospective license migration;
pdf-lib and its bundled dependencies retain their own included licenses.
