# Filecraft: bounded workflow research

Research date: 2026-09-12 WAT (collection timestamps recorded in UTC).

## Decision

Build **Constraint-checked preparation candidates**: a small, deterministic local candidate ladder that finds the least-destructive *tested* output satisfying the user's explicit byte limit, refuses silent regressions, and records the chosen candidate and rejected alternatives in the existing SHA-256 receipt. This extends 0.9 requirements gating rather than adding an unrelated AI/editor feature. It is a recommendation, not implemented software.

The distinguishing proposition is **“prepared against your requirements, with evidence”**, not “better PDF compression.” Target-size compression, offline tools, and signature detection already exist. This research does not establish market-wide novelty.

## Method and coverage

- Inspected [D4Vinci/Scrapling's official README](https://github.com/D4Vinci/Scrapling) and [official docs](https://scrapling.readthedocs.io/en/latest/) before installing anything.
- Actual collection uses **Scrapling 0.4.15 `Selector` for HTML/CSS/XPath extraction**, with Python's standard `urllib.request` as transport. Markdown originals are preserved verbatim and their embedded HTML is parsed with Scrapling. This is a real parser-based Scrapling workflow, **not** a successful use of its Fetcher/browser stack.
- Final ledger: **27 distinct candidate sources; 23 retrieved; 4 Reddit URLs withheld because robots.txt disallowed the research agent**. Retrieved sources comprise 11 official/reference pages, 5 GitHub issues, and 7 PDF24 questions/forum threads. Search results are discovery, not equivalent to retrieved thread bodies.
- Single sequential worker, at least 1.2 seconds between request starts, no crawl expansion, no attachments, login, proxies, impersonation, CAPTCHA workarounds, or denied-page retries. Saved robots policies were checked before each host's content collection. GitHub's listed one-second crawl delay is covered.
- GitHub HTML exposes issue bodies and state, but some activity/reaction components report loading errors. **Not a complete comments export.** No claim about all replies, votes, unique users, or prevalence.
- Convenience sample deliberately sought preparation failures; not representative demand measurement. Old PDF24 reports are historical evidence, not proof of present bugs. Issue claims were read, not reproduced against current competitor releases.

[PUBLIC-SOURCES.md](PUBLIC-SOURCES.md) lists every source and snapshot digest. Full source copies, response headers, discovery dumps and extraction ledgers remain local and are excluded from publication. They are not licensed training data.

## Findings: recurring versus anecdotal

### 1. Recurring: “smaller” is not “meets my requirement”

- [Stirling-PDF #4442](https://github.com/Stirling-Tools/Stirling-PDF/issues/4442), September 2025, reports non-monotonic compression levels and an 8 MB target yielding 0.215 MB when a less-aggressive result was preferred. Retrieved page marks it closed; this is historical demand evidence, not an assertion the current release is broken.
- [Stirling-PDF #4428](https://github.com/Stirling-Tools/Stirling-PDF/issues/4428), September 2025, reports requested targets not reached and includes logs saying maximum optimization was reached without meeting target size. Retrieved issue is open.
- [PDF24 “file size”](https://help.pdf24.org/en/questions/question/file-size), original question 2009 with later answers, describes a scanned document too large to email and manual iteration over quality settings.

**Inference:** a user needs an explicit requirement verdict, the least destructive acceptable option, and a clear “cannot meet this limit” outcome; not an unconditional success toast after a transform. Do not promise arbitrary targets are achievable.

### 2. Recurring across tools: transforms can increase size

- [OCRmyPDF #1620](https://github.com/ocrmypdf/OCRmyPDF/issues/1620), January 2026, reports output 1.38× larger despite no claimed optimization savings.
- [PDF24 compression issue](https://help.pdf24.org/en/forums/topic/pdf24-v8-0-1-compression-issue), 2016–2017, contains reports that scans became larger and lower quality settings harmed quality. One participant explicitly could not share sensitive source documents.
- [PDF24 “Only save reduced size”](https://help.pdf24.org/en/forums/topic/pdf24-compress-only-save-reduced-size), 2017, asks to avoid manually removing non-beneficial candidates across hundreds of files. A maintainer reply acknowledges the request; do not assume it remains unimplemented.
- [OCRmyPDF optimization documentation](https://ocrmypdf.readthedocs.io/en/latest/optimizer.html) explains that overall size may increase and optimization behavior depends on installed tools. It distinguishes lossless from lossy levels.

**Inference:** independently measure final bytes, preserve the original, and reject a size-regressing candidate when size reduction is the goal. A hash confirms artifact identity, not visual fidelity or semantic preservation.

### 3. Recurring reliability theme: heavy batches need bounded work and validation

- [Stirling-PDF #3489](https://github.com/Stirling-Tools/Stirling-PDF/issues/3489), May 2025, reports a large image-heavy PDF, high memory use, and HTTP 504; marked closed as not planned in retrieved HTML.
- [PDF24 merge 70 documents](https://help.pdf24.org/en/forums/topic/merge-70-documents-9-pages-each-into-one-document/), beginning 2018, describes lengthy processing and damaged output; another participant describes blank output after a multi-step OCR/merge workflow.
- [PDF24 merge big files](https://help.pdf24.org/en/forums/topic/merge-big-files-doesnt-work-or-makes-blank-pages/), 2024, reports errors and blank-page problems with a workaround.

**Inference:** local execution removes a network timeout path but does not magically remove memory limits or corrupt PDFs. Candidate generation must be cancellable and budgeted, with output parse/page-count checks. Page-count equality alone does not detect blank rendered pages.

### 4. Important but anecdotal in this sample: signed-document mutation

[Stirling-PDF #5142](https://github.com/Stirling-Tools/Stirling-PDF/issues/5142), December 2025, asks for explicit consent to invalidate signatures during OCR. It is closed. [OCRmyPDF security docs](https://ocrmypdf.readthedocs.io/en/latest/pdfsecurity.html) confirm why OCR cannot preserve these signatures while modifying the document. Treat this as a safety constraint, not proof of broad demand or a claim about legal validity in every jurisdiction.

### 5. Reddit: discovered, not scraped, not counted as validated demand

The saved search response includes [a personal-document/visa 300 KB thread](https://www.reddit.com/r/pdf/comments/1nctlr5/reduce_size_of_pdf_file_without_using_online_tool/) and [a WordPress upload-size thread](https://www.reddit.com/r/Wordpress/comments/1k0nnr7/file_size_limit_how_to_overcome/). The index excerpt suggests privacy and readability tension; **the original Reddit pages were not fetched** because robots.txt disallowed access. Some other indexed results look like product promotion. Do not use these snippets to infer authentic user counts, present-day platform limits, or willingness to pay. Four initial unverified candidate URLs were superseded; retained separately for audit, never treated as evidence.

## One feasible feature: Constraint-checked preparation candidates

Proposed minimum scope, contingent on parent checking the existing implementation:

1. Input: explicit maximum bytes (show decimal MB versus MiB), required page count/order, and a preservation policy. Use existing local requirements profiles; do not guess a destination portal's rules.
2. Preflight: parse input; detect encryption/signature flags if the local engine supports reliable inspection. Unknown checks remain **unknown**, never pass. For this MVP, refuse signed-document mutation rather than invent signature-preservation guarantees.
3. Generate a fixed, ordered, small list of candidate recipes, each **from the untouched original**. Prefer original/no-op when already compliant, then lossless, then explicitly consented lossy recipes. Bound by candidate count, time, memory/disk and cancellation. No binary search assumption: compression can be non-monotonic.
4. Reopen outputs and check actual byte count, parser validity, expected page count, and available text-layer checks. Present visual comparison for lossy outputs; do not label a numeric DPI floor as proven readability. Keep unsupported preservation checks visible.
5. Choose the first passing recipe in the declared least-destructive order. If none passes, say “No tested candidate met these requirements”; never claim mathematical impossibility or silently upload/flatten/delete pages. Splitting is a separate user-approved workflow only when the destination permits multiple files.
6. Receipt includes source and output hashes, profile/schema revision, recipe/engine versions and parameters, measured results, check states, candidate rejection reasons, and user consent. Do not claim bit-identical builds across engine versions merely because the recipe is deterministic.

Suggested acceptance fixtures (to create separately, not scraped personal documents): already-compliant no-op; impossible byte ceiling; size-increasing optimization; non-monotonic candidates; signed/encrypted input; text-layer retention; malformed output; cancellation; insufficient disk; exact byte-boundary conditions. Test a fake engine's selection logic separately from real PDF fixtures. Browser and desktop capabilities may differ; unsupported browser operations must be explicitly unavailable, not secretly sent to a server.

## AI online strategy: honest and optional

**No Filecraft model has been trained, no training dataset has been licensed, and no GPU/account authorization was supplied. This work trained nothing.** Public issue/post access grants no blanket training license.

Keep the complete preparation path local and deterministic. If online assistance is later introduced, use a separately enabled hosted model to propose a *draft* requirements profile from instructions the user intentionally supplies, or explain a local failure report. User reviews every rule; a strict schema and the local engine decide pass/fail. The model must not author receipts, override failing checks, execute arbitrary commands, or silently upload documents.

Before release: choose an actual provider and budget; document region, retention, training-use terms, subprocessors, deletion, and outage behavior. Default to minimal redacted diagnostics rather than document content; explicit consent for each upload class. “No training” is a claim to verify in provider terms, not assume from an API label. Online AI unavailable must not disable the core workflow. Use rights-cleared synthetic/owned documents for evaluation; reject scraped personal posts as training examples. Any later fine-tuning requires separate licensing, consent, evaluation and compute decisions.

## Read the Docs onboarding (not performed)

[Official RTD tutorial](https://docs.readthedocs.com/platform/stable/tutorial/index.html) and [configuration overview](https://docs.readthedocs.com/platform/stable/config-file/index.html) were actually retrieved.

Parent/repository owner should: prepare a docs-only dependency set and a version-2 `.readthedocs.yaml`; select MkDocs for Markdown or Sphinx as appropriate; pin Python/builder dependencies; specify config path; create/verify an RTD account; authorize GitHub access with the necessary organization approval; import the **actual final** repository/default branch; inspect the first build logs; then enable/check PR previews, failure notifications and stable/latest version behavior. Do not claim the desired slug or custom domain is available until verified. RTD pages show both older tutorial examples and newer config templates: do not cargo-cult the tutorial's Python 3.8 example.

No RTD account was accessed, repository imported, webhook created, DNS changed, or documentation deployed. Root docs/config remain the parent's responsibility.

## Scrapling multilingual README approach

The [official README](https://raw.githubusercontent.com/D4Vinci/Scrapling/main/README.md) places prominent language badges near the top, linking to separate `docs/README_*.md` files. Its listed translations include Arabic, Spanish, Brazilian Portuguese, French, German, Simplified Chinese, Japanese, Russian and Korean. [Arabic](https://raw.githubusercontent.com/D4Vinci/Scrapling/main/docs/README_AR.md) and [French](https://raw.githubusercontent.com/D4Vinci/Scrapling/main/docs/README_FR.md) files were actually retrieved; other translation bodies were not reviewed.

Adopt the discoverability pattern, not an unmaintainable claim of full localization: canonical English README, native-language links only for files that exist, shared commands/identifiers preserved literally, a “last reviewed against” version marker, translator review for safety/privacy wording, and a visible fallback for outdated sections. Start only with languages maintainers can review. README translation is not proof the UI, CLI errors or full RTD manual is localized. Never copy Scrapling's own anti-bot claims into Filecraft's product claims.

## Execution issues and limits

The generic extraction backend returned 403 before page retrieval; ordinary direct HTTP reached the official pages. Base Scrapling installed successfully. Importing `scrapling.fetchers` required optional browser-related packages; a fetchers-extra install timed out during Playwright/Patchright downloads. No browser binaries were installed, no desktop dependencies modified. The completed collector deliberately uses the lightweight parser-only installation. Unneeded transport dependencies were uninstalled and the research-only download cache removed to recover disk.

Everything produced lives under `research/filecraft` or `build/filecraft-research-env`; no runtime, website, root docs, Git state, remotes or commits were changed. This is bounded research and an implementation recommendation, not competitor QA, customer validation, a trained AI product, or a hosted-docs deployment.
