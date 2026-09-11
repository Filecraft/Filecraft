# Security and privacy

Report vulnerabilities privately:
https://github.com/gonisulaimann/Prepare/security/advisories/new

Include the affected surface/version, steps and a minimal synthetic sample.
Do not upload confidential documents. No response-time or bounty promise is made.
Beta distribution is not a security certification.

## Trust boundaries

Prepare processes explicitly selected local files. Runtime conversion does not
need accounts, uploads, analytics, remote scripts, cloud APIs or automatic engine
installation. Website/release retrieval uses GitHub hosting and normal network
logs. Build-time dependency/notice retrieval is separate from runtime. Files
selected through cloud-backed providers may sync independently.

Desktop: Python/Tk with Pillow, PDFium, pypdf, reportlab and cryptography; optional
user-installed Tesseract/FFmpeg. Separate disposable workers, bounded input and
request sizes and deadlines reduce accidental harm. They are not a complete
OS sandbox or guarantee against native decoder vulnerabilities. macOS/Windows
allocations are not hard-contained. No blanket hostile-file or sanitizer claim.

Browser/extension: bundled local PDF parser and dedicated worker. Strict CSP,
no remote executable code. The extension requests no host permissions and has
no content script, portal access, download interception or externally connectable
bridge. Static extension workers avoid requiring eval/Blob-worker privileges.
Browser workers have deadlines, not a hard memory cap. Malicious compressed PDFs
can exhaust browser memory. Browser/OS software remains trusted infrastructure.

Historical native image/mobile products have different codec/limit boundaries;
consult their tagged documentation rather than applying suite claims to them.

## File integrity and confidentiality

- Desktop conversion snapshots the selected regular file into private staging;
  parsers never receive the caller's path. Output uses exclusive atomic hard-link
  publication on supported local filesystems. Existing destinations are rejected.
- Receipt verification opens regular files defensively and hashes a bounded stream.
  Files being concurrently modified are not a filesystem-wide immutable snapshot.
- Cancel can race with a copy already published; inspect the destination. Killed
  workers may leave private staging files. This is not secure erasure.
- Passwords travel over worker stdin, not command arguments or preferences.
  User-added text, receipts and profile descriptions may contain sensitive data.
- Browser download collision/overwrite behavior belongs to the browser. Save a
  new name in a local folder. No document autosave is intentionally provided.
- Receipts are unsigned and editable. SHA-256 matching is byte identity relative
  to the chosen receipt, not authentication, certification or approval.

## Parser and output limits

Desktop: 100 MiB input/output, 100 PDF pages, 20 million image pixels, bounded
text/XML expansion and 180-second worker deadline. Archive support is ZIP/GZ
creation, not extraction. Office XML parsing rejects unsupported/ambiguous order
metadata; conversion is text-first. Optional FFmpeg is called without a shell
with restricted local protocols/demuxers; it is not an untrusted-media sandbox.

Browser: ordinary PDFs only; active features, forms, signatures, encryption and
annotations are rejected. 10 files, 20 MB per file, 50 MB total, 100 pages and
30-second jobs. PDF copying can retain embedded resources and visible private
information. Neither surface promises removal of all active content or metadata.

OCR can be wrong. Rasterization loses text/interactivity/signatures. Full PDF
conformance, accessibility, visual fidelity and portal acceptance remain separate
review obligations. Keep authoritative originals and review exported copies.

## Distribution

Windows packages are unsigned. macOS packages are not Developer ID notarized.
Do not disable security controls to run them. Extension ZIPs are not store
approval; Firefox temporary installation is not signed AMO distribution. Keep
the OS/browser/dependencies patched and review qualification per release.
