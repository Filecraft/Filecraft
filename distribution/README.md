# Consumer distribution

This directory builds installers, not new document-processing features. Product
version comes from `product.json`. The previous published release remains intact.
Beta.2 corrects one observed first-run layout bug and introduces installer packaging.

## Build and qualification

`.github/workflows/distribution.yml` freezes the exact candidate source and builds:

- macOS ARM64 and Intel: Filecraft.app inside a read-only drag-to-Applications DMG.
- Windows x64: Inno Setup per-user installer, Start menu entries and uninstaller.
- Ubuntu 24.04 amd64: DEB, desktop entry and `/usr/bin/filecraft`.

The Windows lifecycle runs using a restricted, medium-integrity token derived
from the existing interactive user. Admin groups and privileges are removed;
the test independently rejects admin membership. The CI-only token launcher is
not part of the installer and never weakens UAC or machine security policy. The Ubuntu GUI gate
uses Xvfb, X11 and Openbox. Both exercise OS-input import/export, then quit and
relaunch. All installers undergo installed-runtime conversion tests, same-version
reinstall checks where implemented, and content/permission inspection.

macOS automated checks mount the DMG, inspect the Applications link/Finder layout,
copy the app, check code-signature integrity and exercise its frozen runtime. They
explicitly do not claim GUI export. Release qualification also needs actual GUI
import/export/quit/relaunch evidence for the exact final artifact on each supported
architecture; ARM64 evidence is not evidence for Intel.

Run portable regressions with:

    python -m unittest discover -s distribution/tests -v

Use Python 3.13 for packaging. `runtime-lock.json` records the unchanged historical
beta.1 archives used during initial investigation, not inputs for beta.2 CI.
`fetch_runtime.py` verifies size and checksum before extracting those archives.

## Release contract

`manifest.py` assembles all four consumer artifact slots from final packaging
metadata and checksum sidecars. Missing, duplicated, stale, or corrupt artifacts
fail validation. Do not point the website to candidate artifacts.

After native qualification and review, create a new release tag at the exact
qualified commit; never move an existing tag. Upload the qualified bytes and
sidecars to a draft release. Publish only artifacts whose complete journey passed.
Then run `manifest.py <artifact-directory> --public`: it resolves the remote tag,
compares the source commit, downloads public bytes and checksum sidecars, and
records the actual publication time. Upload that verified manifest and use it
as the website's `release-manifest.json`. Verify the remote manifest matches too.

The website generator refuses unpublished or incomplete manifests. Historical
releases, portable archives and browser extensions remain separate. No extensions
are rebuilt by this workflow. Readmes and current-version links must be generated
or synchronized from this manifest before promoting the release.

## Signing boundary

Unsigned is the default; passing tests is not a signature or notarization.
macOS ad-hoc signatures seal bundle bytes but establish no publisher identity.
Gatekeeper is expected to reject current candidates. No bypass is part of packaging.

For a future authorized macOS signing build, configure a Developer ID Application
identity in the build machine's Keychain and a `notarytool` Keychain profile. Set
`FILECRAFT_SIGN_IDENTITY` to the identity name and `FILECRAFT_NOTARY_PROFILE` to the
profile name; these contain references, not passwords. The packager signs nested
code, submits for notarization, requires Accepted, staples supported containers,
validates signatures and calculates hashes after final modification. This optional
credentialed path still requires real signed GUI and Gatekeeper qualification;
it has not been qualified without credentials.

Windows currently emits unsigned installers only. Enabling trusted signing must
sign the launcher/runtime before Inno compilation and the installer/uninstaller
through a configured Inno SignTool hook, followed by native signature and timestamp
verification. Do not flip the metadata boolean or claim a publisher based on
configuration alone. See `docs/SIGNING.md` for identity eligibility and safe setup.
Never put credentials in source, chat or command logs. CI qualification receives
no signing secrets. Source and dependencies remain reviewable but neither checksums
nor notarization guarantee absence of defects or malicious dependencies.

## Installation, upgrades and uninstall

Quit Filecraft before upgrading. There is no automatic updater or background
service. Keep your previous installer for rollback. macOS replaces the app in
Applications; Windows uses the same per-user installation identity; Ubuntu uses
the package manager. New-version upgrade and rollback testing remain required
in addition to same-version reinstall gates.

No file associations are registered. Exported files belong outside installation
directories. Removing the app/package does not remove documents saved elsewhere.
Optional OCR/media engines remain separately installed tools, not bundled downloads.

## Reproducibility limits

Runtime versions and packaging recipes are pinned. macOS packaging dependencies
are hash-locked. DMG filesystem timestamps/signatures and installer build metadata
mean byte-for-byte reproducibility is not promised. Preserve the source commit,
runner/tool/dependency provenance, final digest and qualification evidence for each
published artifact. Installer existence alone is never release readiness.

## Preserved store foundations

The earlier store-readiness checklist is retained unchanged in
`STORE-FOUNDATIONS.md`. It is historical guidance, not a current publication claim.
Mobile stores and extension marketplace work are outside this phase.
