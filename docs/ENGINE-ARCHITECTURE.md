# Local document engine: architecture direction

## Decision

Separate readiness and workflow semantics from codec implementation. Start with a
small dependency-free JavaScript engine that runs identically in Node and a
browser. This delivers shared rules to the already useful Portable UI and a real
CLI without bundling another runtime. Node is a CLI prerequisite, not hidden in
the downloadable archive. Native Swift/Java converters remain maintained adapters;
this release does not falsely claim they already execute the shared JS engine.

For future native hosts, evaluate a small Rust/C ABI core with the same versioned
conformance fixtures before replacing these rules. Do not add a JS interpreter
to a 25 KB Android application merely for architectural symmetry. Benchmark an
actual codec/parser workload before selecting Rust, C++, WASM or a PDF library.
The product must not accumulate independent interpretations of profile rules.

## Layers

  UI / CLI / automation
      -> profile + document evidence + declarative operations
      -> readiness evaluation and immutable job plan
      -> bounded platform codec adapter
      -> candidate output
      -> independent evidence collection and validation
      -> exclusive or provider-mediated export

Evidence has provenance: header inspection, decoded image, parsed PDF, rendered
page, user declaration. Header magic is not structural validity. Never promote
unknown into pass, nor treat a JSON-supplied claim as independently verified.
A readiness result is scoped to its profile and actual checks, not general legal
acceptance or readability certification.

## Document and history

Assets identify immutable originals; pages refer to assets and transformations.
Order/rotation/duplicate operations create new manifests. Keep large bytes outside
history and bound both history depth and pages. Materialized output is disposable
until verified. Persist projects only by explicit request; avoid recording full
paths in ordinary diagnostics. Version profile/workflow/manifest schemas and fail
closed on unsupported fields or operations. No executable profile scripts.

## Jobs and resources

Job IDs scope cancellation, progress and outputs. Limit active decodes, input
bytes, decoded pixels, page count, temporary bytes and history independently.
Native codec calls may not be interruptible; cancellation must be checked before
and after them. Do not race a still-running job against UI edits. A settings or
page change invalidates the previously prepared result.

Treat jobs as isolated state machines: queued, inspecting, processing, verifying,
ready, exporting, cancelled or failed. Export is not successful until the final
write and available readback checks succeed. Provider-based readback can fail;
say so instead of claiming an integrity guarantee.

## Extension and localization boundary

Plugins begin as allowlisted adapter interfaces, not downloaded arbitrary code.
Each adapter declares formats, supported facts, capabilities and resource limits.
Untrusted parsing should eventually run in a killable worker/process sandbox;
a JS module boundary alone is not a security sandbox. Unsupported PDF/OCR/forms/
PDF-A/encryption facts stay unknown until a qualified adapter exists.

Rule identifiers and structured values belong in the engine; translated messages
belong in UI catalogs. English is the first catalog. Profile names are user data,
not executable templates. CLI machine output uses stable codes and no ANSI prose.

## Privacy and filesystem

No engine network API, telemetry or account. Browser CSP blocks outbound connects;
Android has no INTERNET permission. Mac currently lacks OS sandbox enforcement.
OS sync/cloud providers, website hosting and extension permissions are external
boundaries, explicitly documented. Never promise forensic deletion: snapshots,
swap and journaling may retain bytes. Preserve originals; exclusive create for CLI
outputs, private temporary directories, bounded reads and no implicit recursive
folder traversal. Archive import must validate paths before extracting anything.

## Qualified scope

The existing raster-PDF converters stay stable. The shared engine first powers
profile checks, manifests and CLI evidence; arbitrary PDF editing, OCR, encryption,
PDF/A and intelligent content classification require additional reviewed adapters.
Mobile quality requires real device, accessibility, memory-pressure and provider
qualification. Compiling a shell does not establish platform support.
