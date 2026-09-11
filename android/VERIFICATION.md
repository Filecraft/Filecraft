# Verification of the experimental Android slice

## Executed locally (macOS arm64)

- Downloaded and checksum-verified Temurin 17.0.15+6 and Google command-line tools
  11076708 into ignored `android/.toolchain`; installed compile SDK 36 revision 2
  and build-tools 36.0.0. No system Java modification.
- Tests were written before their production classes. Initial javac failures for
  missing Geometry/Policy/Engine/Copy and UI contracts were observed, followed by
  successful JVM tests and Android compilation.
- `python3 android/build.py --core`: PASS geometry for A4/Letter/original, invalid
  dimensions/limits, exact byte cap, cancellation, decimal MB parsing, streaming
  copy hash verification, corruption, truncation and cancellation.
- `python3 android/build.py`: PASS real aapt2/javac/D8/zipalign build of unsigned
  native app and instrumentation APK, below the hard 1 MB budget.
- Repeated build: byte-identical app APK verified by comparing complete bytes.
- `aapt2 dump permissions`: only `package: com.prepare.app`, no permissions.
- Manifest inspection: min API 28, target/compile API 36, version
  `0.5.0-experimental` / `500`.
- ZIP inspection: DEX present; no signature entries. Release output stays unsigned.

## Explicitly not passed

Local ARM64 emulator system-image download was too slow for the bounded task and
was stopped; no Android device was attached. **Instrumentation was compiled but
not executed locally.** The real PDF rendering, EXIF, native cancellation/size,
SAF-intent and UI tests are honest failing gates in Ubuntu CI, not stub successes.
The parent must push the actual commit and inspect API 28 / 36 results before
claiming native engine/device verification. See workflow `android.yml`.

No production signing key was generated, no store submission took place, and no
APK was published. `test-device.py` generates only an explicitly disposable test
identity when invoked and preserves the unsigned release APK. Physical-device,
complete SAF end-to-end, accessibility, memory-pressure, image-fidelity and store
gates remain in `store/LISTING.md`. Independent parent review remains required.

## Reuse notes

Android PdfDocument is not AutoCloseable: explicitly close it in finally.
Compile instrumentation separately against app classes plus android.jar; a custom
framework Instrumentation avoids bundling test libraries. Never treat `adb shell
am instrument` exit code alone as a pass: require explicit runner success output.
Normalize ZIP timestamps and order before zipalign for repeatable SDK-only builds.
Keep recreation caches per activity session to avoid deleting a still-running
cancelled worker's files. Provider save verification must reopen and compare
actual bytes, not trust close() or a successful write return.
