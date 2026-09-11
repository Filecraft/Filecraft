# Performance and verification

## Local release-core measurement

Measured on 2026-09-11 on a MacBook Air with Apple M4 (10 cores), 16 GB
memory, macOS 27.0 build 26A5425a; Swift 6.4, arm64 release build.

Command (after compilation):

```sh
BIN="$(swift build -c release --show-bin-path)"
/usr/bin/time -l "$BIN/PrepareChecks" --stress --fixtures build/demo
```

Observed exit status: 0. All behavioral checks and 12 stress batches passed.

| Observation | Result |
| --- | ---: |
| Total wall time, entire checks + stress invocation | 5.98 s |
| User CPU time | 2.51 s |
| System CPU time | 1.49 s |
| Maximum resident set size | 147,243,008 bytes (140.4 MiB) |
| Peak memory footprint reported by `time` | 105,300,808 bytes (100.4 MiB) |
| Swaps reported by `time` | 0 |

This is a single synthetic regression workload, not a representative scan
benchmark, a per-document latency promise or a UI responsiveness measurement.
The stress loop uses twelve batches of twenty copies of a generated fixture.
The invocation also generates fixtures and runs correctness checks. Images,
macOS codecs, CPU load and chosen budgets materially change real performance.
Compilation is excluded. Logs are included as release assets.

## Correctness coverage

The executable harness checks PDF reopen/render, final byte limits, input
limits, overwrite rejection, original preservation, cooperative cancellation,
EXIF correction, metadata sentinel omission, PNG/JPEG/HEIC, rendered clockwise
rotation, all page rotations, Original/A4/Letter geometry, white margins,
invalid settings, selected-page extraction and identity-based list navigation.

Source preview is capped at a 1600-pixel longest edge; output attempts range
from 2400 to 960 pixels. Neither is an original-resolution forensic comparison.

## Leak-tool caveat

A separate `leaks --atExit -- PrepareChecks --stress` invocation passed the
functional workload but returned status 1: the tool reported two allocations
(384 bytes total) associated with the async test executable's top-level
fixture array and printed string. It also warned that the process was not
debuggable, restricting inspection. This is not a clean leak certification;
it does not establish that the UI or long-running sessions are leak-free.
The functional release gates do not depend on this restricted leak scan.

## Toolchain note

This machine's default Swift 6.4 `swiftbuild` backend emits linker search-path
warnings for absent optional CommandLineTools Developer framework/library
directories. Builds and checks complete successfully with Swift compiler
warnings treated as errors. A cross-check using `--build-system native` also
compiled successfully without those linker warnings; that backend itself is
deprecated. The project does not hide the warnings or modify system directories.
The default, supported build path remains `swift build`.

Minimum supported deployment target is macOS 14. The local run above does not
constitute testing on every supported macOS version or Intel hardware.
