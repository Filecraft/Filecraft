# PDF auto-fit: bounded candidates, not a compression promise

Filecraft desktop and CLI can try two local PDF candidates, in order:

1. Original bytes, unchanged. If every requirement passes, publish an exact copy.
2. Structural content-stream compression with pypdf. Publish only if every requirement passes, the result does not exceed the source size, and page geometry/count and extracted text match.

No image downsampling, rasterization, removed pages or generative reconstruction is attempted. If neither candidate fits, no destination is published. A limit smaller than the available representations may be impossible.

## CLI

    Filecraft-Desktop prepare input.pdf --target pdf --output fitted.pdf --max-bytes 2000000 --auto-fit

On Windows use `Filecraft-Desktop.exe`. A profile with an explicit `constraints.bytes.max` can replace `--max-bytes`. Source invocation is `python desktop/launch.py` followed by the same arguments.

The JSON result includes `receipt.candidates.selected` and an ordered `attempts` list with recipe, measured bytes, engine version and mechanical checks. Save the receipt object, not the entire command response, to use the existing verification command.

## Desktop

Choose a PDF source, PDF output and the `fit` PDF operation. Set Maximum bytes. Keep Pages blank, rotation zero and passwords empty. Export to a new filename. Preview the actual saved result and save its receipt.

## Refusals and limits

- Encrypted PDFs and detected signature fields/signatures are refused, even if an unchanged copy could meet the limit. Use a separate signature-aware workflow.
- Page selections, rotation, passwords, image quality, annotations and other transformation options cannot be combined with fit.
- Failed or unknown required facts are not accepted candidates.
- The existing 100 MiB, 100-page and disposable-worker deadline bounds still apply.
- Mechanical text/geometry equality is not complete semantic or visual equivalence. Forms, attachments, active content and document structure still require review. This is not a sanitizer.
- Ordinary Copy/Optimize operations retain their separate semantics; the no-size-growth candidate rule applies specifically to fit.
- The browser workspace and extensions do not yet implement this desktop candidate workflow.

The original source is snapshotted for processing and never overwritten. Output publication remains exclusive: a competing destination file is preserved rather than replaced.
