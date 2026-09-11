# Third-party code and runtime parser guards

See [vendor/README.md](vendor/README.md) and [vendor/PROVENANCE.json](vendor/PROVENANCE.json)
for exact upstream sources, licenses and hashes. `vendor/LICENSE` is an unchanged
alias of pdf-lib's MIT `LICENSE.pdf-lib`; all other dependency notices are retained.
The minified UMD itself is byte-for-byte upstream; runtime guards live in document.js.

Upstream reports [#1777](https://github.com/Hopding/pdf-lib/issues/1777)
(DecodeStream buffer growth) and [#1776](https://github.com/Hopding/pdf-lib/issues/1776)
(XRef stream widths) motivated explicit allocation/parser gates. These are issue
reports, not a claim of a CVE or JavaScript memory corruption.

Before any untrusted parsing, document.js locates the internal shared DecodeStream
prototype using a tiny constant Flate stream through the exported decode function.
DecodeStream is **not** exported by this pin. ensureBuffer is wrapped on its actual
prototype; the wrapper validates numeric requests and rounded capacities **before**
the original allocator executes. Per-decoder capacity is capped at 32 MiB and
cumulative capacity growth across an API job at 64 MiB. A promise queue serializes
jobs sharing this vendor instance and resets accounting after success or failure.
Loading document.js therefore also adds the per-stream guard to direct uses of
this PDFLib instance; only PreparePDF API jobs get cumulative accounting.

The exported PDFXRefStreamParser.forStream factory is wrapped **before construction**
(and thus before XRef decoding) to require exactly three W widths, integer 0–4
bytes each, not all zero, Size at most 100,000, and bounded paired Index ranges.
This intentionally rejects valid PDFs requiring wider fields; it avoids the
upstream 32-bit width loop behavior rather than pretending to support it safely.

Regression tests exercise real zlib-compressed ObjStm bombs, cumulative expansion,
invalid allocation requests, XRef widths and huge counts. These gates do not bound
all allocations/CPU inside every PDF syntax path or content stream decoder. V8
worker quotas and termination remain required; OS process memory limits are needed
for a hard total-memory boundary. No broad sanitization/security guarantee follows.
