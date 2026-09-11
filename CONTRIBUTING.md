# Contributing to Prepare

Prepare is a small, native document workbench, not a cloud document platform.
Contributions should make a real image-to-PDF handoff safer, clearer or faster.
Bug reports, accessibility testing, documentation and focused code changes all help.

## Start here

- Search existing [issues](https://github.com/gonisulaimann/Prepare/issues) first.
- Discuss new features before building large changes. Include the user problem,
  a local-only approach, memory implications and a way to verify correctness.
- Never attach real identity documents, medical records or private images.
- Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Report vulnerabilities using [SECURITY.md](SECURITY.md), not public issues.

## Build and run

Requires macOS 14+ and a Swift 6 toolchain (Xcode command-line tools). Apple
Silicon is the released architecture; Intel source builds are not release-tested.
No package dependencies are downloaded.

```sh
git clone https://github.com/gonisulaimann/Prepare.git
cd Prepare
swift run Prepare
swift run PrepareChecks
swift run -c release PrepareChecks
swift build -c release -Xswiftc -warnings-as-errors
bash scripts/package.sh
```

The bundle is `build/Prepare.app`. `PrepareChecks` is an executable integration
harness, not an XCTest target: use `swift run PrepareChecks`, not `swift test`.
For repeated 20-page batches, run `swift run -c release PrepareChecks --stress`.
All its fixtures are generated locally and cleaned up after the run. Use
`--fixtures build/demo` when you deliberately want to keep synthetic samples.

## Architecture and non-negotiables

Read [architecture](docs/ARCHITECTURE.md). Keep image work off the main actor,
use bounded ImageIO thumbnails, and process pages serially. Every visual edit
must invalidate the prepared result and review acknowledgment. Cancellation
must never return an exportable stale result. Preserve input ordering and
source files. Never add telemetry, accounts, upload paths, hidden network
lookups, runtime dependency downloads or an automatic updater.

## Pull requests

1. Branch from `main` and keep one concern per change.
2. Write a regression check, run it to see it fail, then implement the fix.
3. For image changes, assert exported pixels as well as PDF geometry and size.
4. Run the commands above. Test keyboard-only operation, a narrow window,
   errors, cancellation and changes made after preparation.
5. Update README/CHANGELOG when behavior changes. Include test output and
   synthetic before/after evidence in the PR, not generated binaries.
6. Disclose substantial AI assistance. You are responsible for understanding,
   reviewing and verifying every submitted line; untested generated work is
   not a contribution ready for review.

Use Swift's normal naming conventions, four-space indentation and small,
readable helpers. Do not reformat unrelated code or introduce dependencies
without discussion. Tests must not depend on network access or private files.

## Licensing

Contributions are accepted under the same Hippocratic License 3.0 core terms
as the project. You must have permission to contribute the work. Do not copy
in code whose license is incompatible. There is no copyright assignment or
CLA. This is ethical-source software, not OSI-approved open source.

## Maintainer workflow

Goni Sulaiman ([@gonisulaimann](https://github.com/gonisulaimann)) maintains the
project and makes final scope and release decisions. Reviews should explain
correctness and privacy tradeoffs, not just style. There is no promised
response SLA. See [the release checklist](docs/RELEASING.md) for shipping gates.
