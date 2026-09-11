# Store submission foundations — not submissions

The downloadable builds are not store-certified. Source is inspectable under
Hippocratic License 3.0 core; its ethical-use restrictions may exclude some
free-software repositories. Do not replace the license with MIT to pass a check.

## Shared metadata

See `listing.json`: truthful base listing, local-only privacy, owner identity,
source/license/support URLs and explicit platform status. Before submission:
provide a monitored support contact, screenshots from the actual current app,
accessibility notes, age/content rating, region/trader/tax information as required,
and owner-controlled signing credentials. Review store rules again at submission.
No billing, accounts, ads, analytics or conversion networking are designed in.
System pickers can expose cloud-backed providers: choose local storage for a
strict zero-cloud workflow. OS/browser behavior is outside the engine's control.

## Mac App Store

`macos/Prepare.entitlements` is a candidate sandbox profile, NOT enabled in the
GitHub release. Add an Xcode archive/export target, security-scoped URL lifecycle,
sandbox integration tests, Apple distribution identity/provisioning, privacy
manifest/API audit and App Store Connect listing before submission. Existing
ad-hoc signature cannot substitute for this. Do not grant network entitlements.
https://developer.apple.com/documentation/xcode/configuring-the-macos-app-sandbox

## Microsoft Store

The current Windows artifact is a portable browser bundle, not EXE/MSIX. A future
native system-WebView host needs explicit local origin/CSP/navigation limits,
file-picker integration and end-to-end offline tests. Do not simply submit a
ZIP as a Windows executable. Reserve identity in Partner Center, choose a supported
packaging model, then produce and test signed MSIX/App Installer or the approved
unpackaged flow. No installable MSIX is claimed by these foundations.
https://learn.microsoft.com/en-us/windows/apps/publish/

## Linux package managers

`linux/org.prepareapp.prepare.desktop` provides metadata for a future installed
launcher. It is intentionally not installed today: no `prepare-portable` executable
is packaged. Define local browser invocation and sandbox policy, source archive
hash, reproducible package builds, distro license review and installation/removal
tests before shipping DEB/RPM/Flatpak. Bundling an entire browser would violate
our download budget; investigate system-browser integration first.
https://docs.flatpak.org/en/latest/manifests.html

## Google Play

The Android module owns its build manifest and test configuration. Before Play:
owner-controlled long-lived upload key, Play App Signing enrollment, production
application ID review, Android App Bundle pipeline, current target API compliance,
data safety form, public privacy policy, accessibility and phone/tablet tests,
store graphics and any account-specific closed-testing requirement. Test-signed
or unsigned engineering artifacts are not Play submissions. Never reuse a CI
throwaway signing key for production updates.
https://developer.android.com/google/play/requirements/target-sdk
https://developer.android.com/studio/publish/app-signing

## Release gate

A config file is not store readiness. No submission proceeds until actual builds,
platform regression tests, install/update/uninstall checks and license/signing
reviews pass. Account enrollment, legal attestations and key ownership remain
maintainer tasks; no credentials or legal declarations have been invented.
