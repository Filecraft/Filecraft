# Store foundation — NOT SUBMITTED

- Name: Prepare
- Application ID: `com.prepare.app` (ownership/reservation not verified)
- Version name/code: `0.5.0-experimental` / `500`
- Minimum Android: 9 / API 28; compile and target API 36
- Category suggestion: Productivity; no ads, no purchases, no login
- Short description: Prepare local JPEG and PNG images as size-limited PDF copies.
- Full description: Choose up to 20 local images, select A4, Letter or original
  aspect pages and margins, then prepare a PDF under your specified byte limit.
  If supported resolution reductions cannot fit, Prepare reports failure rather
  than saving an oversized file. Save a new copy with Android's document picker.
  Original files stay unchanged. No OCR or PDF input. Experimental: inspect output
  legibility before submitting important documents.
- Data Safety draft: no developer collection or sharing; no network permission.
  Review document-provider behavior and the privacy policy before attestation.
- License: current project-owned source is Apache-2.0. The historical published
  0.5 APK retains Hippocratic 3.0; a source license change does not relabel it.
  LICENSE and NOTICE must accompany any newly built distribution.

## Gates before any public store release

- [ ] API 28 and 36 emulator CI green for the exact commit
- [ ] Physical low-memory and recent devices: large images, 20 pages, provider errors
- [ ] SAF multi-select and save: cancellation, denied permissions, full disk,
      unavailable/removable providers; interrupted save and cleanup
- [ ] TalkBack, large font/display scale, RTL, keyboard/switch access, rotation,
      background/foreground and process death
- [ ] JPEG EXIF rotations/mirrors, transparent PNG, color profiles, corrupt inputs,
      output visual quality and metadata inspection
- [ ] Production application ID ownership and privacy/support HTTPS URLs confirmed
- [ ] Original adaptive launcher icon and store artwork/screenshots finalized
- [ ] Content rating, target audience, Data Safety and legal review completed
- [ ] Production signing chosen by owner; securely retained outside this repository
- [ ] Store-required AAB built/validated with a separately pinned bundletool pipeline
- [ ] Store testing track, pre-launch report and policy acceptance

Current output is an **unsigned APK**, not an upload-ready AAB or installable
production release. No publishing, production key generation or store assertions.
