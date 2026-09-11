# Dependency and provenance policy

Original Prepare source remains under Hippocratic License 3.0 core. This is
ethical-source, not OSI-approved open source. A dependency's permissive license
does not change the root license or imply ownership of upstream code.

## Shipped runtime components

- Native macOS: Apple frameworks provided by the operating system; no bundled
  third-party runtime. Framework rights remain with Apple.
- Image Portable and readiness engine: original dependency-free JavaScript.
- Android: platform Java/framework APIs; no runtime libraries or INTERNET
  permission. SDK and test tools are not inside the runtime artifact.
- PDF Workbench / PDF CLI: locally bundled pdf-lib, separately MIT licensed.
  Its upstream package, exact version, integrity, vendored hashes and license
  are recorded in `pdf/THIRD-PARTY.md` and `pdf/vendor/`. Preserve those notices
  in both the source ZIP and offline browser bundle. Never fetch it from a
  CDN at runtime.

## Build/test-only components

Playwright (pinned in portable/package-lock.json) drives Chromium and Firefox.
PyMuPDF is installed only for independent PDF parsing/rendering in tests and
is not distributed inside application or source ZIPs. Its separate license
still applies to users of that test tool. Java/Android SDK tooling and Python
packaging utilities are likewise build/test dependencies, not a change to
the application license. Do not describe a test dependency audit as proof
that a vendored runtime library has no vulnerabilities.

## Release gates

- Check upstream package provenance and hashes before vendoring updates.
- Retain original upstream license text and all required attribution.
- Inspect the generated archive inventory, not just the source tree.
- Audit lockfiles and vendored dependencies separately.
- Pin GitHub Actions by reviewed commit SHA; verify runtime migration notes.
- Run secret scans on staged changes and inspect their scope. Do not upload
  private fixtures or credentials to test vendors or analysis services.
- Record actual audit findings, tool limitations and unresolved advisories.
  No parser is claimed malware-proof. Size/time/process boundaries supplement
  rather than replace dependency review and security updates.
