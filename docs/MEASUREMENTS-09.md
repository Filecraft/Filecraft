# 0.9 local measurements

Measured macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.13.15.

Synthetic flat white RGB scan, 1600×2200; unrepresentative of real compression complexity.

Warm filesystem; five sequential trials; CLI wall time, not GUI startup or peak memory. Pillow-only baseline lacks Prepare validation, provenance, publication protections. Not a competitive speed ranking.

| Operation | Median seconds, five trials |
| --- | ---: |
| Pillow subprocess transform only (not equivalent validation/publication) / jpg | 0.0599 |
| worker-start+import+transform+validate+hash+publish / jpg | 0.1065 |
| worker-start+import+transform+validate+hash+publish / pdf | 0.1569 |
| worker-start+import+transform+validate+hash+publish / zip | 0.0850 |

Run `build/desktop-env/bin/python scripts/benchmark_workspace.py` to reproduce.
Raw per-trial observations are saved as build/v09-benchmark.json. Not a startup,
OCR, complex-document, batch or memory claim. Those dimensions remain unmeasured
and no website marketing number is derived from this small synthetic test.
