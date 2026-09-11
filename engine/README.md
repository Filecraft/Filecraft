# Shared document engine and source CLI

Local-only, dependency-free JavaScript. The shared file is CommonJS in Node and a browser UMD global named `DocumentEngine`. It performs no network requests, pixel decoding, file rendering, or institutional verification. Repository licensing remains unchanged; see the root `LICENSE` (also included in source bundles).

## Run

**Install Node.js 22 or later first.** No `npm install` is needed. The ZIP is source, not a standalone binary. From the repository or extracted ZIP root:

```sh
node engine/cli.js --help
node engine/cli.js inspect "/path/to/résumé.png"
node engine/cli.js validate "/path/to/file.pdf" engine/profiles/local-pdf-example.json
node engine/cli.js profile validate engine/profiles/local-image-example.json
node engine/cli.js profile import engine/profiles/local-image-example.json
node engine/cli.js profile export engine/profiles/local-image-example.json
node engine/cli.js workflow engine/examples/document.json engine/examples/workflow.json
node --test engine/test/*.test.js
```

All output, including errors, is JSON on stdout. Paths are positional and may be absolute or relative; quote spaces. There are no workflow-provided paths, shell commands, plugins, registry, implicit file writes, or network imports. Profile validate/import/export all validate the input and emit canonical, recursively key-sorted JSON. Redirect stdout to a **different** file to save it; redirection to the input file would truncate it before the CLI starts. The CLI never edits source documents. `workflow` only changes a document **model**, always dry-run.

Exit codes: `0` inspection/profile/workflow success or readiness READY; `2` NOT_READY; `3` UNKNOWN; `4` bad command/JSON/schema/input limit/model/action; `5` filesystem/I/O error; `130` cancellation (SIGINT). Inspection success is not readiness success. A malformed recognized header is reported in inspect diagnostics rather than as a filesystem failure.

## Evidence and readiness

`evaluate(document, profile)` produces `{version:1, profileId, status, checks}`. Each check is `{code, state, params, remediation}`. States are `pass`, `fail`, `unknown`; status is `NOT_READY` if any check fails, otherwise `UNKNOWN` if any required check is unknown, otherwise `READY`. Structural validation is **always required**, even for an empty constraint set. Codes and remediation identifiers are stable; adapters should localize them and render parameter strings as text, never HTML.

Stable check codes: `STRUCTURE`, `FORMAT`, `BYTES`, `PAGE_COUNT`, `FILENAME`, `PAGE_DIMENSIONS`, `PAGE_ORIENTATION`. Error objects carry `.code`, `.message`, and sometimes `.params`. Inspection adds evidence diagnostics: `PIXELS_NOT_DECODED`, `PNG_PRIMARY_CANVAS_ONLY`, `JPEG_RAW_DIMENSIONS`, `PDF_NOT_PARSED`, `UNRECOGNIZED_FORMAT`, `MALFORMED_HEADER`, `HEADER_LIMIT`, `DIMENSION_LIMIT`.

The Node inspector reads at most 256 KiB of headers, uses 64 KiB streaming SHA-256 buffers, and rejects files larger than 512 MiB. It compares open-file metadata before/after reading to detect common concurrent modifications (not an adversarial snapshot guarantee). The hash covers every read byte, not just headers. PNG IHDR signature, length, CRC, dimensions, depth/color and method fields are checked. JPEG marker segment bounds and SOF dimensions are checked. **Neither format is decoded or fully structurally validated.** PNG page count 1 represents its primary canvas, not APNG frame count. JPEG dimensions are raw SOF dimensions; EXIF orientation is not parsed. Oversized/unseen headers remain unknown. A recognized PDF signature never triggers regex page counting: PDF pages and structure remain unknown. Encrypted, malformed or signed PDFs require a real PDF adapter.

Consequently the CLI cannot claim READY based on header inspection alone. It may identify a known failure or an unknown. An adapter may provide `structuralValidation:'pass'` only after actually validating with its format parser/decoder. Model JSON can assert facts but is not proof; do not treat untrusted model JSON as independently verified evidence. Examples/profiles are illustrative personal rules, not requirements issued or verified by any institution.

## Adapter API

```js
// Browser: <script src="../engine/document-engine.js"></script>
const E = require('./document-engine.js'); // omit in browser; use DocumentEngine
const profile = E.validateProfile(E.parseJSON(profileText));
const document = E.createDocument({
  format: 'png', bytes: 1234, filename: 'scan.png', pageCount: 1,
  structuralValidation: 'unknown',
  pages: [{id: 'page-1', width: 640, height: 480, unit: 'px', rotation: 0}]
});
const readiness = E.evaluate(document, profile);
let history = E.createHistory(document);
history = E.applyAction(history, {op:'rotate', pageIds:['page-1'], degrees:90});
history = E.undo(history);
history = E.redo(history);
const result = await E.runWorkflow(document, {version:1, steps:[
  {op:'duplicate', pageIds:['page-1']}
]}, {signal: abortController.signal});
// result: {version, dryRun:true, stepsCompleted, document, history}
```

`createDocument` requires all top-level fields shown. Formats: `png`, `jpeg`, `pdf`, `unknown`. Unknown bytes, filename, pageCount, width, height, or unit are `null`, not fabricated zeroes. Width/height are positive bounded numbers; units `px` or `pt`; rotations `0/90/180/270`. Page IDs are unique, nonempty strings up to 100 UTF-16 code units. Optional `sourceId` references the adapter's original page. Model collections and returned objects are deeply frozen copies; caller objects are not frozen. Page dimensions refer to the source coordinate system; effective dimensions swap at 90/270 degrees. The adapter is responsible for normalizing source orientation.

Actions: `duplicate`, `delete`, `reorder`, `rotate`, `extract`; all have `pageIds`. Rotate additionally requires signed right-angle `degrees` (90/180/270 or negatives). Reorder must name every page exactly once. Extract creates a replacement model in the selected order; undo restores the previous model. Delete cannot remove every page. Duplicate inserts each copy after its source, generates deterministic `copy-N` IDs, and preserves `sourceId`. All actions require a complete page model and invalidate `bytes` and structural evidence; **export and inspect again** before evaluating a rendered result. History is an opaque in-memory object from `createHistory` (not accepted from arbitrary JSON). Undo/redo preserves exact earlier evidence and clears the redo branch on new edits.

`validateWorkflow` validates every step before execution and rejects unknown operations/properties. `runWorkflow` is async and yields between steps, checks AbortSignal before/after steps, rejects with `CANCELLED` without mutating or returning a partial model. Optional trusted `yieldControl: async () => ...` is for adapter scheduling/tests, never JSON. Zero-step workflows still honor cancellation. A failed later action likewise does not mutate the input.

Limits: 1 MiB UTF-8 JSON; 256 modeled pages; 32 undo/redo snapshots; 128 workflow steps; filename 255 UTF-16 code units; page dimensions up to 1,000,000 units. Profile filename maxLength counts Unicode code points. Filename rules support extension allowlists, maximum length, and ASCII-only, not regexes or paths. Page/dimension min/max comparisons are inclusive. Profile dimension units never convert implicitly. Incomplete page evidence yields unknown checks. Runtime schema validation is authoritative and also enforces cross-field min/max ordering beyond the JSON Schema files.

## Test and package

```sh
node --test engine/test/*.test.js
python3 engine/test/package_test.py
python3 engine/package.py
```

Python 3.9+ is needed **only to build/test the source ZIP**, not to use the CLI. Packaging writes `engine/dist/document-engine-source.zip` and `.zip.sha256`, includes the existing root LICENSE unchanged, and excludes generated output/caches. CI runs Node 22 and 24 tests on Linux, Windows and macOS, then packages and checks a source ZIP on Linux. CI upload is an artifact, not publication or a signed/notarized application. Independently verify the SHA-256 checksum after downloading. Cross-platform CI execution must be checked in the actual Actions run; a workflow definition alone is not evidence that those runners passed.
