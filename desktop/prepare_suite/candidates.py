"""Bounded local PDF candidates, inside the existing disposable worker only.

Mechanical checks are not complete semantic or visual fidelity verification.
The caller owns the snapshot, private staging file and process deadline.
"""
import shutil
from pypdf import PdfReader, PdfWriter, __version__ as pypdf_version
from .pdf_ops import _geometry, _safe, _Invalid
from .requirements import evaluate, output_facts


def _retention(reader):
    return ([_geometry(page) for page in reader.pages],
            [page.extract_text() or '' for page in reader.pages])


def _optimize(source, output):
    with PdfReader(source) as reader:
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        for page in writer.pages:
            page.compress_content_streams()
        with open(output, 'wb') as stream:
            writer.write(stream)


def _preflight(reader):
    if reader.is_encrypted:
        raise _Invalid('Auto-fit refuses encrypted PDFs, including empty-password encryption.')
    if not 1 <= len(reader.pages) <= 100:
        raise _Invalid('Auto-fit requires 1 to 100 PDF pages.')
    # Walk the reachable object graph, not get_fields(): unnamed fields and
    # annotation-only widgets must not escape signature detection. Bound cycles.
    from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject
    pending = [reader.trailer]
    seen = set()
    count = 0
    while pending:
        obj = pending.pop()
        if isinstance(obj, IndirectObject):
            obj = obj.get_object()
        if not isinstance(obj, (DictionaryObject, ArrayObject)):
            continue
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        count += 1
        if count > 100000:
            raise _Invalid('Auto-fit PDF structure exceeds the inspection budget.')
        if isinstance(obj, DictionaryObject):
            def resolved(key):
                value = obj.get(key)
                return value.get_object() if isinstance(value, IndirectObject) else value
            if resolved('/FT') == '/Sig' or resolved('/Type') == '/Sig' or '/ByteRange' in obj:
                raise _Invalid('Auto-fit refuses PDFs containing signature fields or signatures.')
            pending.extend(obj.values())
        else:
            pending.extend(obj)


@_safe
def fit(source, output, profile, filename):
    attempts = []
    selected = None
    with PdfReader(source) as reader:
        _preflight(reader)
    for recipe in ('original', 'structural-optimize'):
        if recipe == 'original':
            shutil.copyfile(source, output)
        else:
            with PdfReader(source) as reader:
                original_geometry, original_text = _retention(reader)
            _optimize(source, output)
        facts = output_facts(output, 'pdf', filename=filename)
        readiness = evaluate(facts, profile)
        checks = list(readiness['checks'])
        checks.append({'code': 'sourceByteUpperBound',
                       'state': 'pass' if 0 < facts['bytes'] <= source.stat().st_size else 'fail'})
        if recipe != 'original':
            with PdfReader(output) as reader:
                geometry, text = _retention(reader)
            checks.extend([
                {'code': 'pageGeometry', 'state': 'pass' if geometry == original_geometry else 'fail'},
                {'code': 'textRetention', 'state': 'pass' if text == original_text else 'fail'}])
        passed = all(check['state'] == 'pass' for check in checks)
        attempts.append({'recipe': recipe, 'bytes': facts['bytes'],
                         'engine': 'pypdf ' + pypdf_version,
                         'parameters': {} if recipe == 'original' else {'contentStreamCompression': True},
                         'status': 'passed' if passed else 'rejected', 'checks': checks})
        if passed:
            selected = recipe
            break
    if selected is None:
        raise _Invalid('No tested candidate met these requirements; no copy was published.')
    return {'warnings': ['No rasterization or image downsampling. Mechanical page geometry and extracted text checks '
                         'do not prove complete semantic or visual fidelity. Review the output; active content may remain.'],
            'candidates': {'selected': selected, 'maxCandidates': 2, 'attempts': attempts}}
