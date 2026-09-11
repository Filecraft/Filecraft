# Filecraft release checklist

Release publication is an explicit maintainer action after independent review and exact-source CI. The canonical website is https://filecraft.github.io/, published from `Filecraft/filecraft.github.io`, branch `main:/`.

Never publish to or modify `gonisulaimann/gonisulaimann.github.io`. The protected personal site is outside this migration. The application repository's `docs/index.html` is a legacy project-Pages redirect only.

## Current desktop, CLI, workspace and extension release

1. Update `product.json`, `desktop/prepare_suite/__init__.py`, current README and changelog. Run `python3 scripts/check_product.py` and `python3 scripts/test_filecraft_identity.py`. Do not change historical tags or rename old assets.
2. Install `desktop/requirements.txt`; run `PYTHONPATH=desktop python -m unittest discover -s desktop/tests -v` (set the environment variable separately on Windows). Include GUI, candidate/receipt, publication-race and parser regressions. Use synthetic files.
3. Run browser regressions with `npm --prefix portable ci` and `npm --prefix portable test`. Install the project's Playwright test browsers first when needed. Run `python3 extension/package.py`, package tests and installed Chromium/Edge/Firefox workflow tests.
4. Run the four-target desktop CI matrix: Windows x64, Linux x64, macOS ARM64 and macOS x64. `python desktop/package.py` creates current Filecraft archives. `desktop/check_frozen.py` must exercise the actual executable, including auto-fit, receipts, AES and rendering. Optional engines are qualified separately.
5. Audit each downloaded native archive with `python3 scripts/audit_desktop_archive.py <archive.zip>`. Check architecture, current identity, exact project/dependency notices and checksums. The current legal audit supports the Apache 0.9+ line; older packages need their version-specific audit, not a forced current license comparison.
6. Build browser ZIP with `python3 scripts/package_workbench.py`. Compare reproducible extension rebuilds and verify extracted workflows, not merely ZIP integrity.
7. Build docs with `python -m mkdocs build --strict -f docs/mkdocs.yml`. Read the Docs hosting is not established by a successful local build; verify any separately authenticated deployment before linking it.
8. Inspect staged changes for credentials, private fixtures, scraped page bodies and unintended artifacts. Require independent review plus successful CI for the exact release commit. Keep signing, platform and feature limits explicit.
9. Create an annotated version tag at the reviewed commit. Publish a prerelease with actual tested assets and SHA-256 sidecars. Do not replace a stable release label with a beta merely to make `/releases/latest` point at it; current-beta entry points are the website and README.
10. Download every public asset without authentication, verify its size/checksum and inspect extracted packages. Verify the published tag, source SHA and release status through GitHub's API.
11. Sync the separate organization checkout with `python3 scripts/sync_site.py <filecraft-site-checkout>` and `python3 scripts/sync_releases.py <filecraft-site-checkout> --current <published-tag>`. Both must reject other remotes before writing. Generate docs, product pages and sitemap; run site identity/link/SEO, privacy/offline and responsive tests.
12. Publish the site, wait for deployment, then verify live home/current downloads, `/releases/`, workspace, 404, disclosures, actual assets and every canonical URL. Recheck the protected site's unchanged remote state.

## Signing and runtime boundaries

Desktop beta binaries are unsigned/not notarized. No Developer ID, notarization, Windows certificate, app-store approval or hostile-file sandbox is implied. Do not recommend disabling operating-system protection. Keep complete extracted runtimes together. Tesseract and FFmpeg are optional separate local engines, not silently downloaded dependencies.

Chromium/Edge extensions use unpacked developer-mode installation; unsigned Firefox packages use temporary installation. Store access, signing, terms and review are separate gates. Safari packaging is not qualified.

## Retained historical source

The small Swift image utility retains actual `Prepare` and `PrepareChecks` command/bundle identities. If maintaining that legacy surface, use its version-specific instructions and budgets; do not apply its tiny archive budgets to the broader desktop suite. Its CI remains a regression gate, not a new Filecraft native release claim.

Native Android development and CI are retired; no `android/build.py` command belongs in the current checklist. Android source remains in historical tags. No native iOS/iPadOS release is maintained. Historical assets retain their original bytes, names and license terms.
