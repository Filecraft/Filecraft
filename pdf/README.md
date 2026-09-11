# Prepare PDF core

Dependency-local Node 22+ and browser PDF page operations. No runtime npm install,
network access, server, shell execution, or document upload. Project code retains
the repository's **Apache-2.0** license (`../LICENSE`) prospectively. Historical
releases keep their original Hippocratic terms. Vendor code retains
its original licenses; see [vendor notes](vendor/README.md).

## Shared API (stable paths for the browser workbench)

Load `pdf/vendor/pdf-lib.min.js`, then `pdf/document.js`: global **PreparePDF**.
CommonJS: `const PreparePDF = require('./pdf/document.js')`.
The host must execute browser operations in a dedicated Worker and terminate it
on cancellation/timeout. A Blob worker can concatenate these two local files for
`file://` support. The core does not create workers or implement cancellation.
Do not execute untrusted PDF operations on a browser UI thread or main Node thread.

```js
const info = await PreparePDF.inspect(bytes); // Uint8Array or Node Buffer
// {pageCount, pages:[{width,height,rotation}], byteLength, warnings}
const output = await PreparePDF.transform([firstPDF, secondPDF], [
  {source:1, page:0, rotation:90},
  {source:0, page:2, rotation:0},
  {source:0, page:2, rotation:-90}, // duplicate is intentional
], {maxBytes: 10 * 1024 * 1024});
// output is Uint8Array, never a download or filesystem write
```

- `source` and `page` are **zero-based** integer indices. Every entry must include
  `rotation`, an added clockwise integer multiple of 90. Order and duplicates are
  preserved. Rotation is normalized to 0/90/180/270, added to inherited rotation.
- Width and height are MediaBox dimensions in PDF points, before rotation. Cropped
  appearance may differ. Output is reloaded and checked against source-derived
  page count, dimensions, rotation, and all five page boxes, including origins.
- Errors reject with `Error.code`: `INVALID_PDF`, `ENCRYPTED`,
  `UNSUPPORTED_FEATURE`, `INVALID_PLAN`, `LIMIT`, `OUTPUT_LIMIT`,
  `OUTPUT_VALIDATION`. Browser hosts should catch unexpected parser/resource errors
  too and report failure, never infer a valid result from lack of a message.
- `maxBytes` is optional; when provided it must be an integer from 1 to 52,428,800.
  The browser should set its explicit selected budget. Default/hard output cap is
  50 MiB. This is **not compression**: an over-budget result is rejected.
- `await PreparePDF.transformVerified(inputs, plan, options)` returns `{bytes,info}`
  from the same validated output reload, including outputs above the input cap.
- `PreparePDF.limits` and `PreparePDF.version` are read-only exported constants.

### Bounds

1–10 input PDFs; at most 20 MiB (20,971,520 bytes) per input and 50 MiB combined;
1–100 source pages in total; 1–100 output pages. Empty plans, unknown entry keys,
fractional/negative/out-of-range indices, and rotations not divisible by 90 fail.
Each inspect call is capped at 20 MiB. A merged output may exceed 20 MiB, up to the
50 MiB output cap; internal reload verification uses the output limit, but that
large output cannot be supplied as a new input/inspect call.

## CLI

```sh
node pdf/cli.cjs --help
node pdf/cli.cjs --version
node pdf/cli.cjs inspect 'source.pdf'
node pdf/cli.cjs transform --output merged.pdf first.pdf second.pdf
node pdf/cli.cjs transform --output selected.pdf --pages 3,1-2,3 --rotate 90 --max-bytes 2000000 source.pdf
```

CLI pages are **one-based**, unlike the API. Ascending ranges and duplicates are
supported. `--pages` requires exactly one input. Omit it to concatenate all input
pages in input order. Use `--` before dash-leading input paths.

Every outcome is one JSON object on stdout. Success uses `{ok:true,command,result}`
and includes `output` for transforms. Errors use `{ok:false,error:{code,message}}`.
Exit codes: **0** success, **2** usage, **3** filesystem, **4** PDF/plan/bounds,
**5** timeout/worker failure. `--help` and `--version` also return JSON.

Inputs must be regular files. Final-component symlinks, directories, devices and
FIFOs are rejected; parent-directory symlinks are allowed. lstat/open/fstat checks,
no-follow/nonblocking flags where available, bounded reads and post-read stat
checks reduce filesystem races, but are not a hostile-filesystem sandbox. Output
is opened exclusively (`wx`, mode 0600) only after successful validation. Existing
files, including original inputs, hardlinks and symlinks, are never overwritten.
No source is opened for writing. An I/O failure after creating a new output can
leave an incomplete new file; it is reported as failure, never success. Keep
outputs in trusted directories; hostile parent-directory replacement is not covered.

PDF reads/parsing/transforms run inside a Worker with a **30-second timeout**,
**256 MiB V8 old-generation heap**, 32 MiB young-generation and 4 MiB stack limits.
Before parsing, decoder allocation requests are capped at 32 MiB per stream and
64 MiB cumulative capacity growth per API job. XRef widths/counts are validated
before stream construction. See [guard implementation and scope](THIRD-PARTY.md).
Jobs sharing one vendor instance are serialized for reliable budget accounting.
This is not a 256 MiB total-process/RSS limit: native decompression buffers and
ArrayBuffers are outside V8 heap quotas, and workers share a process. Complex PDFs
can exhaust process/OS resources. For hostile documents use OS/container memory
and CPU limits plus filesystem/network isolation. CLI filesystem writes are not
part of the PDF worker's timeout; network filesystems can block OS operations.

## Supported scope and important non-guarantees

Supported: ordinary PDF 1.0–1.7 pages; merge, reorder, duplicate, extract and rotate;
preserved text/vector/image content. Headers must start at byte zero, the final
startxref must point to a table/object, and a terminal %%EOF must be present.
Truncated/obviously malformed PDFs fail. pdf-lib is a repairing, complex parser:
passing these checks is **not** complete conformance validation or a guarantee
that every malformed file will be identified.

Rejected conservatively across parsed object dictionaries: encryption (no password
or ignore-encryption bypass), AcroForm/XFA forms, signatures/permissions/ByteRange,
nonempty annotations (including links), document/page actions, JavaScript,
attachments/embedded files, associated files, portfolios, rich media, common
external/action types. Empty annotation arrays are allowed because pdf-lib creates
them on normal text pages. This may reject otherwise harmless PDFs and is not a
complete detector of all active or malicious PDF features.

**Not a sanitizer, redactor, malware scanner, accessibility checker, OCR engine,
renderer, flattening tool, compressor, PDF/A validator or signature-preserving
editor.** Embedded page resources/content and some metadata may survive copying;
merged outputs do not promise preservation of document-level metadata, bookmarks,
logical reading order, tags, outlines or catalog features. Removing an output page
is not a promise that its sensitive resources are absent. No privacy scrub is
performed. Image/text encodings and content streams are copied, not semantically
validated. A parser pass must not be represented as readable, safe, or accepted by
a submission portal. **Reopen every result in an independent viewer, visually
check every page, then test it in the destination workflow.**

## Verification and standalone source package

```sh
node --test pdf/test/*.test.cjs
python3 -m unittest discover -s pdf/test -p '*_test.py'
python3 pdf/package.py
```

Node tests require no install. Optional Python PDFium checks run only when
`pypdfium2` is installed in the developer environment; it is not bundled or a
production dependency. Tests use generated real PDFs with text/asymmetric shapes,
forms, encryption markers, malicious feature dictionaries, malformed bytes,
shifted/inherited geometry, order/duplicates, size/path bounds and original hashes.
PDFium tests independently verify rendered geometry, retained text and nonblank
renders. They do not certify arbitrary user files.

`dist/prepare-pdf-source.zip` is deterministic, below 2 MB, contains `LICENSE`
and this entire standalone `pdf/` tree including vendor/licenses, CLI, worker,
API, docs and tests. Node modules, build caches and dist files are excluded.
The companion `.sha256` identifies the built bytes. Extract then run the same
commands from the extracted root. Python is needed only to build the ZIP.

## Physical page measurements

Widths/heights are visible CropBox intersected with MediaBox, scaled by
UserUnit, in physical points before separately reported rotation. Original
page boxes are also preserved and compared after export.
