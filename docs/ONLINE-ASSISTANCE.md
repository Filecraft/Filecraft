# Online assistance: decision and safety boundary

Filecraft currently has two delivery modes, not two processing engines:

- Hosted workspace: download the application from filecraft.github.io, then process files locally.
- Offline workspace/desktop: download a release once; no account or connection is needed for supported processing.

Turning the connection off after loading the web workspace does not enable an AI engine. A fresh offline visit is not guaranteed by the hosted site; use the self-contained ZIP for reliable offline startup.

## Why no neural toggle in this release

There is no trained Filecraft model, licensed training corpus, measured evaluation, hosted inference service, retention contract or operated security boundary. A toggle implying those exist would be deceptive. Uploading documents to an arbitrary provider would undermine the product's local-processing guarantee.

The bounded research in [REPORT.md](../research/filecraft/REPORT.md) supports deterministic constraint-checked candidates before generative processing. A hosted assistant may later draft requirements from user-supplied instructions; it must not autonomously execute a transformation or decide that a private document is safe to upload.

## Prerequisites before online inference ships

1. Separate explicit opt-in, exact payload preview, destination and retention disclosure, and an equally functional local path.
2. No uploads on startup, network restoration, file selection or background retry.
3. User-approved requirements validated by the local schema; model output is untrusted data, never commands or executable profiles.
4. Licensed/synthetic evaluation data with measured extraction and instruction-following failures. Fine-tuning only if it beats a simpler baseline on that evaluation.
5. Abuse controls, authentication, secret isolation, deletion/retention implementation, operational cost limits and documented privacy responsibilities.
6. Visible model/version/provider and failure states; disconnecting cannot convert an incomplete cloud result into a verified local output.

No paid inference, training run or cloud document upload has been initiated for this release.
