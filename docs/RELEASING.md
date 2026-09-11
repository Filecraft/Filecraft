# Release checklist

Releases are deliberate maintainer actions, not automatic publications on push.
The macOS CI workflow checks source and packaging. GitHub Pages serves `docs/`
from `main`; there is no JavaScript build toolchain or website dependency tree.

1. Update the version in `scripts/package.py`, README, CHANGELOG and website.
2. Run `swift run PrepareChecks`, release checks, warnings-as-errors and stress
   checks. Record machine, compiler, fixture workload and real measured values.
3. Run `python3 scripts/check-site.py`, then preview `docs/` at narrow and wide
   widths. Check keyboard focus, anchors, download URLs and reduced motion.
4. `bash scripts/package.sh`; inspect the bundle version and arm64 architecture.
5. Run `codesign --verify --strict build/Prepare.app`. Launch the app and test
   add, reorder, rotate, margins, compare, cancellation and new-file export.
6. Unzip into a temporary directory and repeat signature and bundle checks.
   Confirm LICENSE, NOTICE and icon resources are included.
7. Review `git diff --cached` for credentials, private samples and generated
   artifacts. Require green CI before publishing release assets.
8. Tag the exact reviewed commit and publish the ZIP, checksum, LICENSE and
   verification report with `gh release create`. Explain signing status in
   the release notes. Download the assets again and check SHA-256.
9. Verify the public repository, release and GitHub Pages URL independently.

## Signing status

Current builds use an ad-hoc signature and are **not notarized**. Do not claim
otherwise or tell users to disable Gatekeeper globally. Users may need to
approve the app through System Settings → Privacy & Security after attempting
to open it. Corporate policies may forbid running it; building locally is an
alternative, not a policy bypass.

`SIGN_IDENTITY` can select a valid installed Developer ID certificate when
packaging. That only signs the app. Notarization, ticket stapling and fresh
Gatekeeper assessment must be completed separately before changing claims.
Do not publish signing credentials or embed credentials in CI. Intel/universal
builds require their own hardware testing and correct asset architecture names.
