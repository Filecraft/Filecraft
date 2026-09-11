# Dependency and provenance policy

Original Filecraft work in the 0.9 development line uses Apache-2.0. Third-party
components retain separate grants; earlier releases keep their supplied
licenses. See [LICENSING.md](LICENSING.md), root LICENSE and NOTICE.

## Runtime scope by product

- Native Swift macOS app: Apple system frameworks, no third-party Swift packages.
  This does not describe the separately packaged Python desktop suite.
- Image Portable/readiness engine: original dependency-free JavaScript.
- Android experiment: platform Java/framework APIs; platform/SDK rights are not
  transferred to Prepare.
- PDF Workbench / CLI: pdf-lib 1.17.1 UMD, including upstream dependencies.
  MIT notices for pdf-lib, standard-fonts, upng and pako; supplementary zlib
  source notice; Apache-2.0 plus Microsoft attribution for tslib. Preserve
  `pdf/vendor/LICENSE*` and provenance with the generated worker and source ZIP.
  No runtime CDN fetch. Supplementary notice versions do not prove every
  embedded dependency version; see [vendor notes](https://github.com/Filecraft/Filecraft/blob/main/pdf/vendor/README.md).
- Python desktop: direct pins in `desktop/requirements.txt`; actual collected
  distributions/versions in each package's `licenses/DEPENDENCIES.json`.

## Desktop notices

| Component | License / qualification |
| --- | --- |
| Pillow | MIT-CMU and additional native codec/library terms; retain full LICENSE |
| pypdfium2 / PDFium | BSD-3-Clause / Apache-2.0 and build-specific dependency notices; retain author attribution, not only generic templates |
| pypdf | BSD-3-Clause |
| cryptography | Apache-2.0 OR BSD-3-Clause; use Apache-2.0 for this distribution, preserve both upstream texts |
| reportlab | BSD; fonts separately licensed |
| defusedxml | PSFL |
| cffi | MIT-0 in inspected current distribution; verify installed metadata |
| pycparser | BSD-3-Clause |
| charset-normalizer | MIT |
| Python, Tcl/Tk | Their own runtime notices |
| OpenSSL | Exact runtime version's upstream license/copyright/authors, separately for Python and cryptography builds |
| Vera fonts | Bitstream Vera font license retained with fonts |

Native dependencies include PDFium's codec/font/rendering components and
Pillow's native codecs. Keep complete upstream texts, not only this summary.
Filecraft uses the FreeType Project (https://freetype.org/) through applicable
bundled dependencies; FreeType is copyright its respective authors. Detailed
copyrights and terms are retained in dependency license files.

`desktop/package.py` collects Python distribution notices plus Python/Tcl/Tk
texts. On **all platforms**, it detects Python's and cryptography's actual
OpenSSL versions and retrieves exact upstream tagged LICENSE, AUTHORS and
copyright header at build time, recording URLs and hashes. Unknown TLS variants
or unavailable legal text stop packaging; no runtime download is introduced.
This version detection is not a recursive audit of every linked native binary.

New bundles prune unused `DarkGarden*` assets from ReportLab after collection.
Vera remains available for PDF output with `bitstream-vera-license.txt`.
Historical bundles containing DarkGarden remain subject to that font's GPL
with document-embedding exception; do not call those archives wholly permissive.

FFmpeg and Tesseract are optional user-installed subprocess tools, not bundled
by this packager. FFmpeg's license depends on its build/codecs; neither its
terms nor codec patent questions are resolved by the Prepare root license.

## Build/test-only components

Playwright and downloaded browsers are test-only. PyMuPDF is used for independent
PDF checks, not included in the desktop runtime requirements. PyInstaller is a
build tool with its own application-bundling exception. SDKs and test tooling
retain their terms; ensure they do not leak into release archives.

## Release gates

- Verify vendor hashes and retain complete upstream notices and provenance.
- Inspect **each platform archive**, not just this source tree: identify native
  libraries and compare the shipped versions against the collected texts.
- Confirm no DarkGarden files, and verify Vera font + license remain usable.
- Verify root LICENSE/NOTICE and all dependency/native notices are included.
- Preserve Python/PDFium author attribution even where generic license texts
  contain template placeholders. Review additional dependency/native notices.
- Stop publication for missing notices, unknown license/build combinations or
  unreviewed dependencies. Collected metadata is not a complete binary SBOM.
- Keep historical assets/checksums intact; supplemental historical compliance
  notices require a separate release-maintainer action, not silent replacement.
- Pin dependencies/actions, audit runtime and build tools separately, avoid
  private fixtures, and report unresolved findings without security guarantees.
