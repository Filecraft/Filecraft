# Prepare Android — experimental native app

Java + Android framework APIs only. No WebView, runtime dependencies, INTERNET or
storage permissions. Android 9+ (API 28). **Not production/device qualified and not
published.** The unsigned APK cannot be installed until signed. Do not present it
as a finished Android release; the device/store gates are in `store/LISTING.md`.

## Build (macOS, Linux, Windows with Python 3 and JDK 17)

From the repository root:

```sh
python3 android/build.py --core  # JVM tests only
python3 android/build.py         # JVM tests + release and instrumentation APKs
```

On Windows use `python` instead of `python3`. Set `JAVA_HOME` to a JDK 17 home and
`ANDROID_SDK_ROOT` (or `ANDROID_HOME`) to the SDK root. On this development Mac,
the downloaded toolchain is isolated and gitignored under `android/.toolchain`;
`build.py` finds that local installation without changing system Java.

### Toolchain setup, no preinstalled SDK assumed

Use Eclipse Temurin **17.0.15+6** (build pin, not a recommendation to retain an old
JDK for unrelated workloads). Obtain its OS/architecture archive and published
SHA-256 from the official release, verify before extracting:
https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.15%2B6

The verified development Mac archive is
`OpenJDK17U-jdk_aarch64_mac_hotspot_17.0.15_6.tar.gz`, SHA-256:
`1a2fa2bb9ea059cf2c1ab3e296a98e006fb6fdad2bd19ce52df48794eaa1836a`.

Android command-line tools pin: **11076708**. Download from Google's SDK repository
using `commandlinetools-mac-11076708_latest.zip`,
`commandlinetools-linux-11076708_latest.zip`, or
`commandlinetools-win-11076708_latest.zip` at
`https://dl.google.com/android/repository/`. Verify the official checksum before
extracting. Verified Mac archive SHA-256:
`7bc5c72ba0275c80a8f19684fb92793b83a6b5c94d4d179fc5988930282d7e64`.

Unix example after extracting JDK and command-line tools:

```sh
export JAVA_HOME=/absolute/path/to/jdk-home
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_SDK_ROOT=/absolute/path/to/android-sdk
/path/to/cmdline-tools/bin/sdkmanager --sdk_root="$ANDROID_SDK_ROOT" --licenses
/path/to/cmdline-tools/bin/sdkmanager --sdk_root="$ANDROID_SDK_ROOT" \
  'platforms;android-36' 'build-tools;36.0.0' 'platform-tools'
python3 android/build.py
```

Read and accept Android SDK licenses yourself. On Windows use sdkmanager.bat and
set environment variables in PowerShell. Compiler platform is Android 36 **revision
2**, build-tools **36.0.0**, Java source/target 8, min API 28. The Android package
manager can revise platform packages; record `source.properties` for archival
reproduction and use the same revisions. Build has no Gradle/Maven downloads.
ZIP entry order/timestamps are normalized; identical local rebuilds are checked.
Cross-OS bit identity is not yet established. Emulators and platform-tools are
validation tools, not inputs to the release APK.

Outputs (ignored):
- `android/build/prepare-unsigned.apk` and `.apk.sha256`
- `android/build/prepare-tests-unsigned.apk` and `.apk.sha256`

The build includes root LICENSE/NOTICE and `store/PRIVACY.md` as APK assets.
A hard 1,000,000-byte app budget fails the build. The initial implementation is
well below the 250 KB target, before production signing/store processing.

## Tests and test-only installation

`tests/CoreTests.java` runs without Android: geometry, page options, validation,
exact byte cap, cancellation, copy/read-back digest integrity and truncation.
`tests/EngineTests.java` is a custom **framework Instrumentation**, no JUnit or
AndroidX APK dependency: synthetic JPEG/PNG through real PdfDocument and
PdfRenderer, pixel assertions, page count, byte failure, cancellation, invalid
input, cleanup, SAF intent contracts and native UI smoke checks.

With a disposable emulator/device connected (this uninstalls any prior
`com.prepare.app` and `.tests` test installation and its private data):

```sh
python3 android/test-device.py
```

This creates a **disposable TEST ONLY** two-day key in ignored build storage,
signs separate `*-TEST-ONLY.apk` copies, installs and runs them, then deletes the
key even on failure. It never signs or changes the unsigned release APK. It is
not a production signing workflow. Do not publish the test-signed APKs. The
script checks instrumentation output as well as exit status; log is
`android/build/instrumentation.txt`.

`.github/workflows/android.yml` builds on Ubuntu and runs emulator API 28 / 36
with KVM, checks deterministic rebuilds and absence of permissions, and uploads
only **unsigned** APKs/checksums plus logs. CI must pass for the actual parent
commit; writing the workflow is not evidence that it ran.

For eventual owner-controlled signing (no production key is generated here):

```sh
# Use an EXISTING owner-supplied signing identity outside this repository.
"$ANDROID_SDK_ROOT/build-tools/36.0.0/apksigner" sign \
  --ks /secure/outside/repository/owner.keystore \
  --out android/build/prepare-owner-signed.apk android/build/prepare-unsigned.apk
"$ANDROID_SDK_ROOT/build-tools/36.0.0/apksigner" verify --verbose \
  android/build/prepare-owner-signed.apk
```

Let apksigner prompt for credentials; do not put passwords in source, logs or
shell arguments. Google Play generally requires an AAB; this deliberately tiny
SDK-only builder does not claim to produce one. Store submission remains blocked.

## Behavior and bounds

1. SAF `ACTION_OPEN_DOCUMENT`, JPEG/PNG filters, multi-select, LOCAL_ONLY requested.
   Re-select replaces the list; deduped provider-returned order is the PDF order.
2. One worker, one decoded software bitmap at a time. ImageDecoder applies EXIF
   orientation and scales before allocation. Header checks reject >100 MP or
   >65,535 pixels per dimension. Maximum 20 images. No original byte arrays held.
3. Native PDF pages retain drawing data until export; aggregate decoded raster
   budget is approximately 8 MP per attempt, individual longest edge ≤1600 px.
   Retry edges: 1600, 1200, 800, 500, 320 (also clamped by per-page budget).
   This bounds requested rasters, **not total process/native-decoder memory**.
4. A4/Letter portrait, centered aspect-fit, no cropping; original uses oriented
   pixel dimensions as points, capped to 2000-point longest content edge.
   Margins are 0/18/36/72 PDF points; original adds margins around the content.
5. Exact decimal MB limit. A limited stream throws before writing excess; file
   length is checked. Only a fully completed in-budget PDF becomes saveable.
   Cannot-fit means these supported resolution attempts failed, not proof that
   no possible codec/settings could fit. PDFs vary by Android's native writer.
6. Cooperative cancellation between native operations and streaming chunks.
   Native decode/PDF calls and a blocking provider cannot always be interrupted
   instantly. Cancellation does not masquerade as a successful preparation.
7. Save is `ACTION_CREATE_DOCUMENT`, not original overwrite. Streamed output is
   closed and reopened to verify exact byte count and SHA-256 before success.
   Failed saves attempt destination deletion; the UI warns if partial files may
   remain. Select a local location; external document providers may sync on their
   own even though Prepare cannot access the network.
8. Clear drops selection/private PDF, not saved copies or originals. Rotation or
   process recreation resets the workspace explicitly; no persisted URI grants.
   No background service, automatic uploads or persistent content index.

## Release verification still required

The synthetic tests cannot establish all SAF provider behavior, low-memory
safety, accessibility, physical-device performance or store eligibility. Follow
`store/LISTING.md`. Review saved text legibility; raster downsampling is lossy.
No OCR/PDF input/encryption/password, forensic metadata-erasure or universal
instant-cancellation claim is made.

## Verified experimental artifact

API 28 and 36 emulator gates passed run 34589813446. See VERIFICATION.md.
Release artifact `Prepare-0.5.0-android-experimental-UNSIGNED.apk` needs your own
signing for installation; it is not a consumer or Play Store release. Do not
use disposable CI signing identities for updates.
