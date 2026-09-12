# Filecraft

### Make the right copy. Know what changed.

Local document preparation for Windows, macOS, Linux and the browser.
Set requirements, try bounded PDF auto-fit candidates, verify the result and keep a receipt.
No account. No document upload. No subscription gate.

[Download for Windows — 0.10 beta](https://github.com/Filecraft/Filecraft/releases/download/v0.10.0-beta.1/Filecraft-0.10.0-beta.1-desktop-windows-amd64.zip) ·
[All platforms](https://filecraft.github.io/download/) ·
[Try the local workspace](https://filecraft.github.io/workspace/) ·
[Documentation](https://filecraft.github.io/documentation/) ·
[Release archive](https://filecraft.github.io/releases/)

English · [Français](docs/i18n/README.fr.md) · [Español](docs/i18n/README.es.md)

## One workflow, not five utilities

Import → Understand → Prepare → Validate → Verify → Export

- Personal requirements gate desktop exports. Failed checks do not publish a copy.
- PDF operations/previews, images, text-first documents, ZIP/GZ packaging and optional
  local OCR/media engines share an original-preserving worker.
- Receipts bind measured output bytes to SHA-256 and your requirements.
- The PDF web/extension workspace merges, extracts, orders and rotates pages locally.
- Desktop CLI uses the same engine; no GUI or local HTTP server is required.

Receipts are unsigned evidence—not proof of authenticity, safety, accessibility,
visual fidelity or portal acceptance. Office conversion is text-first. Arbitrary
file packaging is not universal conversion. See [limits](desktop/README.md).

## Install

Use the [download page](https://filecraft.github.io/download/) for the actual
published version, architecture, size, checksum and installation instructions.
Windows/Linux x64, Apple Silicon and Intel Mac packages are qualified through
native CI. Binaries are unsigned/not notarized; follow your organization’s policy.
Browser extensions are developer-mode/temporary-install previews, not store listings.
Mobile development is retired; historical releases are preserved in the archive.

## PDF auto-fit

    Filecraft-Desktop prepare input.pdf --target pdf --output fitted.pdf --max-bytes 2000000 --auto-fit

Try original bytes first, then structural compression. Never publish a larger candidate; refuse if neither meets every requirement. No rasterization, no model, no upload. [Limits and evidence](docs/AUTO-FIT.md).

## Develop and automate

Python 3.13 with Tk:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r desktop/requirements.txt
.venv/bin/python desktop/launch.py
.venv/bin/python desktop/launch.py prepare input.png --target pdf --output copy.pdf --max-bytes 2000000
```

On Windows use `.venv\Scripts\python.exe`. Local OCR needs Tesseract; media needs
FFmpeg. Optional engines are not silently downloaded at runtime.

```sh
PYTHONPATH=desktop .venv/bin/python -m unittest discover -s desktop/tests -v
npm --prefix portable ci
npm --prefix portable test
python3 extension/package.py
```

[Architecture](docs/ENGINE-ARCHITECTURE.md) · [Contribute](CONTRIBUTING.md) ·
[Security](SECURITY.md) · [AI contribution rules](AGENTS.md)

## AI development disclosure

This software is developed with AI assistance. The maintainer identifies the
model as OpenAI’s frontier model GPT-6 Astra. The maintainer-supplied estimated
token cost is **$256.09**; supplied counts are inconsistent and **not audited**.
[Full metrics and caveats](docs/AI-DISCLOSURE.md).
This is not a claim that Filecraft ships a fine-tuned neural processing engine.

## License and continuity

Original code: Apache-2.0. Dependencies retain their own notices. Filecraft continues
Prepare through a repository transfer, preserving history and historical releases.
The personal website is untouched. [Migration and compatibility](docs/MIGRATION.md).
