# From documents to readiness

This is a staged product program, not a promise that all capabilities exist.
The detailed 100-entry backlog remains in ROADMAP-100.md; stages below organize
future investment by dependencies and evidence, not an arbitrary feature count.

## 1. Shared foundation — in progress

Shipped source: UI-independent document model, tri-state rules, versioned profiles,
strict JSON validation, bounded undo/redo, cancellable model workflows, bounded
header inspector and hash-streaming CLI. Portable uses shared page operations
and rules. Next gate: one conformance corpus across native and web adapters, safe
project persistence, storage quotas, job isolation and localized UI catalogs.

## 2. Real document evidence

Adopt a maintained PDF parser/renderer after license, vulnerability, binary-size
and sandbox experiments. Acceptance: malformed/encrypted/signed/object-stream
corpus, independently rendered output, no regex page counting, bounded parser
process termination. Add embedded-resource and metadata reports before editing.
Investigate platform OCR and optional separately downloaded local language packs;
measure quality across languages and handwriting without claiming certainty.

## 3. Constraint-directed preparation

Version rules and evidence provenance; add minimum DPI, password policy, metadata
and filename requirements only when adapters can verify them. Search candidate
transformations under time/quality budgets, explain infeasible combinations and
re-evaluate final bytes independently. Profiles remain offline and data-only.
Never label a profile institution-verified without provenance and review.

## 4. Reusable professional workflows

Implement real merge/split/extract, image conversion, deskew, blank-page detection,
metadata management and visual comparison behind reviewed adapters. Then add
batch manifests, resumable jobs, deterministic conflict handling and atomic local
exports. Golden fixtures must verify actual content and visual regressions.
Workflow dry runs remain distinct from rendered/exported output.

## 5. First-class platform products

Desktop: choose thin native shells and reusable codec bindings; benchmark cold
start, peak memory, packaging and accessibility on x64/ARM64 hardware. A browser
ZIP is not a native Windows/Linux app. Start with one justified Linux format.
Mobile: harden Android SAF, signed release process, TalkBack, memory pressure and
physical-device testing; prototype iOS/iPadOS with Files and VoiceOver before
claiming support. No store submissions or enrollment spending without owner setup.
Web: share engine behavior while preserving CSP and no-network document handling.

## 6. Extensible ecosystem

Stable CLI exit/schema contract; typed adapter capabilities; allowlisted plugins;
profile import provenance; threat-modeled extension isolation. No marketplace or
remote code execution by default. Optional intelligence can suggest actions but
cannot override deterministic validation or upload documents implicitly.

## Release gate for every stage

Unit + hostile-input corpus + failure/cancellation tests + rendered/structural
checks + accessibility basics + actual platform CI + downloaded artifact/hash
verification. Release labels must reflect qualification. Record performance
hardware and fixture dimensions; never generalize a small benchmark to all files.

## Differentiation

Acrobat and PDF Expert emphasize broad editing; PDF24 and Stirling PDF expose many
tools; OCRmyPDF adds searchable layers and Ghostscript/ImageMagick enable expert
pipelines. The opportunity here is a transparent readiness contract: requirements,
measured evidence, reversible remedies and verified output, working locally.
This is a product hypothesis, not a claim competitors lack every such capability.
