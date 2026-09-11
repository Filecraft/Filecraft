# Licensing

## Current original work: Apache-2.0

Beginning with the **0.9 development line**, owner-controlled original Prepare
source is offered under the Apache License, Version 2.0. The first intended
release carrying this change is **0.9.0-beta.1**; this document does not claim
that release has already been published. The complete legal terms are in
[LICENSE](../LICENSE); attribution is in [NOTICE](../NOTICE).

This is a prospective source-tree change authorized by the project owner, not
an assertion that the maintainer owns every byte. Third-party components,
legal texts and platform APIs are excluded from the original-work grant.
Generated files inherit the terms of their constituent sources; in particular
`workbench/worker-bundle.js` embeds upstream pdf-lib alongside original code.

Apache-2.0 permits commercial use, modification and redistribution subject to its
conditions, including preservation of license/notices and identification of
modified files. It provides a contributor patent grant, not trademark rights
or a warranty. Read the license rather than treating this summary as new terms.

## Earlier releases remain historical

Previously published releases through **0.8.0-beta.1**, including earlier
platform previews, retain the Hippocratic License 3.0 core supplied with their
original Prepare work. Their upstream dependencies retain separate terms.
Existing tags, archives, checksums and versioned verification reports are not
rewritten. Receiving this source under Apache-2.0 does not replace the license
inside an old downloaded binary. Historical statements about Hippocratic or
the unpublished MIT prototype describe their time, not current policy.

## Third-party exceptions and redistribution

- PDF components: [third-party notes](../pdf/THIRD-PARTY.md), original
  `pdf/vendor/LICENSE*` files and hash/source records in `PROVENANCE.json`.
  The supplementary pako/zlib source header is retained separately; UMD bytes
  are unchanged. Include those files with mixed/generated browser bundles.
- Desktop: preserve the complete distribution-specific `licenses/` inventory,
  including native libraries and fonts. Package metadata alone is insufficient.
  New packaging excludes unused DarkGarden fonts and retains Vera plus its
  Bitstream license. Old distributions containing DarkGarden retain that font's
  GPL-2.0-or-later terms and document-embedding exception; the font is not
  relicensed by this change.
- Frameworks, SDKs, optional user-installed FFmpeg/Tesseract, and build/test
  tools are governed by their own terms. They do not become Apache-2.0 merely
  because Prepare uses or invokes them.

See [DEPENDENCIES.md](DEPENDENCIES.md) for the platform inventory and release
gates. This engineering inventory is not an exhaustive binary audit or legal
opinion. Newly discovered substantive outside contributions require checking
the actual grant; maintainer authority is not copyright assignment.

## License text provenance

`LICENSE` was retrieved unchanged from
https://www.apache.org/licenses/LICENSE-2.0.txt.
SHA-256: `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`.
The Apache Software Foundation publishes that legal instrument; the root
copyright attribution applies to original Prepare work, not authorship of the
license itself. Exact third-party legal text is preserved, not paraphrased.
