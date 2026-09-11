# Prepare

Make the right copy. Know what changed.

Prepare is a local document-preparation workspace built around a useful loop:
**Import → Understand → Prepare → Validate → Verify → Export.**

Set your requirements, make a separate copy, inspect the result and keep a
hash-bound receipt. Mechanical checks are evidence—not a promise of portal
acceptance, visual fidelity, accessibility or safety.

[Website](https://gonisulaimann.github.io/) ·
[Downloads](https://gonisulaimann.github.io/download/) ·
[Local PDF workspace](https://gonisulaimann.github.io/workspace/) ·
[Documentation](https://gonisulaimann.github.io/documentation/)

## Choose a surface

| Surface | Actual scope | Status |
| --- | --- | --- |
| Desktop | Images, text-first documents, PDF operations/previews, optional local OCR/media, ZIP/GZ; personal requirements and receipts | 0.9 beta development; native packages require four-platform qualification |
| Web / offline workspace | PDF merge, order, extraction, rotation, profiles, receipts and byte verification | Browser workflow; not desktop parity |
| Extension | The local PDF workspace in a dedicated browser tab, no host permissions | Chromium/Edge developer-mode package; Firefox temporary-install package; not store-published |
| CLI | Desktop worker commands: `formats`, `prepare`, `verify` | Same bounded worker and original-preserving export |
| Android | Historical image-to-PDF utility | Unsigned 0.5 experiment; no desktop-suite parity |
| iOS / iPadOS | No native application published | Web access is not native app support |

The small [stable 0.5 image tools](https://github.com/gonisulaimann/Prepare/releases/tag/v0.5.0)
and [0.8 desktop beta](https://github.com/gonisulaimann/Prepare/releases/tag/v0.8.0-beta.1)
remain available under their original licenses and feature scope.

## What is different

- Requirements are part of preparation, not an afterthought. Failed desktop
  requirements block output publication; unknown evidence stays unknown.
- Originals and competing destination files are not overwritten by desktop
  exports. Browser downloads follow your browser’s save/overwrite behavior.
- Receipts bind output size and SHA-256 to observed facts and personal rules.
  They are editable and unsigned; matching bytes do not authenticate a document.
- No accounts, document uploads, telemetry, remote conversion or cloud fallback.
  Hosting requests and cloud-synced storage remain separate boundaries.

## Run from source

Desktop: Python 3.13 with Tk, then:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r desktop/requirements.txt
.venv/bin/python desktop/launch.py
.venv/bin/python desktop/launch.py prepare input.png --target pdf \
  --output prepared.pdf --max-bytes 2000000
```

On Windows use the equivalent `.venv\Scripts\python.exe` path. CLI preparation
returns JSON containing a `receipt` object; save that object separately, then:

```sh
.venv/bin/python desktop/launch.py verify prepared.pdf --receipt receipt.json
```

Browser: open `workbench/index.html` with its sibling files intact.
Extension: [build/install and qualification](extension/README.md).

## Important boundaries

Office conversion is text-first, not layout-preserving. ZIP/GZ packaging is not
universal conversion. Lossless optimization may grow files; lossy rasterization
changes fidelity. OCR and media need separately installed Tesseract/FFmpeg.
Desktop packages are unsigned/not notarized. Prepare is not a sanitizer or a
complete hostile-file sandbox. Do not disable OS security protections to run it.

[Exact desktop matrix](desktop/README.md) · [Security](SECURITY.md) ·
[Research and product decision](docs/PRODUCT-DECISION-09.md) ·
[Architecture](docs/ENGINE-ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md)

## License

Current project-owned source: **Apache-2.0**. Third-party components retain their
upstream licenses and notices. Historical artifacts through 0.8.0-beta.1 retain
the Hippocratic 3.0 license under which they were released; history is not rewritten.

[Transition and provenance](docs/LICENSING.md) · [LICENSE](LICENSE) ·
[NOTICE](NOTICE) · [Dependencies](docs/DEPENDENCIES.md)
