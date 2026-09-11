"""Offline PDF operations; call ONLY inside a disposable, bounded worker.

The parent owns input/output byte limits, the process deadline, and a private
empty staging output file. These functions never modify the source. PDF data is
not a sanitizer: preserved annotations, links and actions may remain in exports,
but this module never executes actions, opens links, or initializes PDFium JS.
"""
from contextlib import closing, contextmanager
from functools import wraps
from io import BytesIO
import json
import math
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

MAX_PAGES = 100
MAX_PIXELS = 20_000_000
BASE_WARNING = ('Not a sanitizer: PDF links, actions, attachments and private metadata '
                'may remain; no links or actions are executed by this worker.')


class _Invalid(ValueError):
    pass


def _safe(function):
    """Do not leak parser errors containing source content or passwords."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except _Invalid:
            raise
        except Exception:
            raise ValueError('Cannot process this PDF. Check the password, file integrity, '
                             'supported options and available disk space.') from None
    return wrapped


@contextmanager
def _reader(path, password=''):
    if not isinstance(password, str):
        raise _Invalid('The input password must be text.')
    with open(path, 'rb') as stream:
        reader = PdfReader(stream, strict=False)
        if reader.is_encrypted and not reader.decrypt(password):
            raise _Invalid('This PDF needs the correct input password.')
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            raise _Invalid('Use a PDF containing between 1 and 100 pages.')
        yield reader


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise _Invalid(f'{name} must be an integer.')
    return value


def _dpi(value):
    return max(36, min(200, _integer(value, 'DPI')))


def _page(value, count):
    value = _integer(value, 'Page index')
    if not 0 <= value < count:
        raise _Invalid('Choose a zero-based page index within this document.')
    return value


@contextmanager
def _output(source, output):
    """Open only the parent's empty regular staging file; reject aliases."""
    if os.path.samefile(source, output):
        raise _Invalid('Output must be a separate private empty staging file.')
    flags = os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(output, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size or info.st_nlink != 1:
            raise _Invalid('Output must be a private empty regular staging file.')
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            try:
                yield stream
            except BaseException:
                stream.seek(0)
                stream.truncate(0)
                raise
    finally:
        os.close(fd)


@contextmanager
def _render(source, password, page_index, dpi):
    import pypdfium2 as pdfium
    with _reader(source, password) as reader:
        geometry = _geometry(reader.pages[_page(page_index, len(reader.pages))])
    scale = dpi / 72 * geometry['user_unit']
    # Initialize appearance rendering only: no JS platform, callbacks or action calls.
    with pdfium.PdfDocument(source, password=password) as document:
        import pypdfium2.raw as raw
        if document.get_formtype() in (raw.FORMTYPE_XFA_FULL, raw.FORMTYPE_XFA_FOREGROUND):
            raise _Invalid('XFA visual rendering is unsupported; use an ordinary AcroForm PDF.')
        config = raw.FPDF_FORMFILLINFO(version=2, xfa_disabled=True)
        document.init_forms(config=config)
        if not 1 <= len(document) <= MAX_PAGES:
            raise _Invalid('Use a PDF containing between 1 and 100 pages.')
        with closing(document[_page(page_index, len(document))]) as page:
            width, height = page.get_size()
            if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                raise _Invalid('PDF page geometry is invalid.')
            pixels = (math.ceil(width * scale), math.ceil(height * scale))
            if pixels[0] * pixels[1] > MAX_PIXELS:
                raise _Invalid('Page exceeds the 20 million pixel budget; lower DPI or crop the source.')
            with closing(page.render(scale=scale, draw_annots=True,
                                     may_draw_forms=True, limit_image_cache=True)) as bitmap:
                image = bitmap.to_pil()
                try:
                    yield image
                finally:
                    image.close()


@_safe
def preview(source, output, page=0, password='', dpi=96) -> dict:
    """Render one zero-based page to PNG. DPI is clamped to 36..200."""
    dpi = _dpi(dpi)
    with _reader(source, password) as reader:
        page = _page(page, len(reader.pages))
    with _output(source, output) as stream, _render(source, password, page, dpi) as image:
        image.save(stream, format='PNG')
        width, height = image.size
    return {'output': str(output), 'target': 'png', 'page': page, 'dpi': dpi,
            'width': width, 'height': height, 'bytes': Path(output).stat().st_size,
            'warnings': [BASE_WARNING, 'Preview uses stored appearances; dynamic/XFA form appearance is not guaranteed.']}


def _pages(options, count):
    selected = options.get('pages', list(range(count)))
    if not isinstance(selected, list) or not 1 <= len(selected) <= MAX_PAGES:
        raise _Invalid('Pages must be a nonempty list of at most 100 zero-based indices.')
    return [_page(value, count) for value in selected]


def _copy(reader, selected, rotation):
    writer = PdfWriter()
    if selected == list(range(len(reader.pages))):
        writer.clone_document_from_reader(reader)
    else:
        writer.append(reader, pages=selected, import_outline=False)
        if reader.metadata:
            writer.add_metadata(reader.metadata)
    for page in writer.pages:
        if rotation:
            page.rotate(rotation % 360)
    return writer


def _fill(writer, values):
    if not isinstance(values, dict) or not values:
        raise _Invalid('Provide a nonempty fields dictionary of text or checkbox values.')
    acroform = writer.root_object.get('/AcroForm')
    acroform = acroform.get_object() if acroform is not None else {}
    if '/XFA' in acroform:
        raise _Invalid('XFA forms are unsupported; use an ordinary AcroForm PDF.')
    fields = writer.get_fields() or {}
    normalized = {}
    for name, value in values.items():
        if name not in fields:
            raise _Invalid('A requested field is missing from the selected pages; inspect field names first.')
        field = fields[name]
        if int(field.get('/Ff', 0)) & 1:
            raise _Invalid('A requested field is read-only.')
        if field.get('/FT') == '/Tx' and isinstance(value, str):
            normalized[name] = value
        elif field.get('/FT') == '/Btn' and not int(field.get('/Ff', 0)) & ((1 << 15) | (1 << 16)):
            states = [str(s) for s in field.get('/_States_', []) if s != '/Off']
            if not isinstance(value, bool) or len(states) != 1:
                raise _Invalid('Checkbox fields require true/false and one supported on-state.')
            normalized[name] = states[0] if value else '/Off'
        else:
            raise _Invalid('Only text strings and ordinary checkbox boolean fields are supported.')
    writer.update_page_form_field_values(None, normalized, auto_regenerate=False)


def _ocr(source, output, stream, selected, password, dpi, target, options):
    language = options.get('language', 'eng')
    if not isinstance(language, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,32}(?:\+[A-Za-z0-9_]{1,32}){0,7}', language):
        raise _Invalid('OCR language must name installed local languages, for example eng or eng+fra.')
    executable = options.get('tesseract', 'tesseract')
    if not isinstance(executable, str) or not executable or '\x00' in executable:
        raise _Invalid('Choose a local Tesseract executable.')
    writer = PdfWriter() if target == 'ocr-pdf' else None
    texts = []
    # Only rendered pixels leave PDFium. Tesseract receives no PDF or password.
    with tempfile.TemporaryDirectory(prefix='prepare-ocr-', dir=Path(output).parent) as work:
        image_path = Path(work) / 'page.png'
        base = Path(work) / 'recognized'
        for index in selected:
            with _render(source, password, index, dpi) as image:
                image.save(image_path, format='PNG', dpi=(dpi, dpi))
            command = [executable, str(image_path), str(base), '-l', language, '--dpi', str(dpi),
                       'pdf' if writer is not None else 'txt']
            try:
                subprocess.run(command, shell=False, check=True, timeout=60,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               env={**os.environ, 'OMP_THREAD_LIMIT': '1'})
            except subprocess.TimeoutExpired:
                raise _Invalid('Local OCR exceeded the 60 second per-page deadline.') from None
            except (OSError, subprocess.CalledProcessError):
                raise _Invalid('Local OCR failed. Check Tesseract and the requested installed language.') from None
            if writer is not None:
                with _reader(base.with_suffix('.pdf')) as recognized:
                    if len(recognized.pages) != 1:
                        raise _Invalid('Local OCR produced an invalid page count.')
                    texts.append(recognized.pages[0].extract_text() or '')
                    writer.append(recognized, import_outline=False)
            else:
                texts.append(base.with_suffix('.txt').read_text(encoding='utf-8'))
        if writer is not None:
            writer.write(stream)
        else:
            stream.write('\n\f\n'.join(texts).encode('utf-8'))
    return language, texts


@_safe
def convert(source: str, output: str, target: str, options: dict) -> dict:
    """Export into an existing private empty file, returning factual metadata.

    Targets: pdf/png/jpg/txt/ocr-pdf/ocr-txt. Images export one source ``page``
    (default 0); text/OCR/PDF use zero-based ``pages`` in given order. Text pages
    are separated with form feeds. Annotation ``page`` indexes the OUTPUT order
    and ``annotation`` is a plain text note (1..10000 characters). Raster DPI
    36..200 and JPEG quality 1..95 are clamped. OCR uses installed languages only
    (``language=eng``), local ``tesseract`` executable and a 60s/page timeout;
    it rebuilds rendered pages, not original interactive PDF structures.
    PDF ``rotation`` is additional clockwise degrees (multiples of 90).
    Parent supplies an EXISTING private empty regular staging file, enforces
    byte/process limits and removes failed staging files. Source is never edited.
    """
    if not isinstance(options, dict):
        raise _Invalid('Options must be a dictionary.')
    if target not in ('pdf', 'png', 'jpg', 'txt', 'ocr-pdf', 'ocr-txt'):
        raise _Invalid('Unsupported PDF export target.')
    password = options.get('password', '')
    dpi = _dpi(options.get('dpi', 96))
    quality = max(1, min(95, _integer(options.get('quality', 80), 'Quality')))
    warnings = [BASE_WARNING]
    result = {'output': str(output), 'target': target, 'warnings': warnings,
              'before_bytes': Path(source).stat().st_size}
    with _reader(source, password) as reader, _output(source, output) as stream:
        if target in ('png', 'jpg'):
            page = _page(options.get('page', 0), len(reader.pages))
            with _render(source, password, page, dpi) as image:
                image.save(stream, format='PNG' if target == 'png' else 'JPEG', quality=quality)
                result.update(page=page, width=image.width, height=image.height, dpi=dpi)
            warnings.append('Image export loses selectable text, forms and interactivity; stored appearances only.')
        elif target in ('ocr-pdf', 'ocr-txt'):
            selected = _pages(options, len(reader.pages))
            language, texts = _ocr(source, output, stream, selected, password, dpi, target, options)
            result.update(pages=selected, page_count=len(selected), dpi=dpi, language=language,
                          characters=sum(map(len, texts)), encrypted=False)
            warnings.append('OCR is local and may misrecognize text; verify the result. Rendered output loses editable forms, annotations, vector fidelity and signatures.')
            if not any(text.strip() for text in texts):
                warnings.append('OCR found no recognizable text; the output has no searchable text.')
            if reader.is_encrypted:
                warnings.append('Output is unencrypted; the input password is not retained.')
        elif target == 'pdf':
            selected = _pages(options, len(reader.pages))
            rotation = _integer(options.get('rotation', 0), 'Rotation')
            if rotation % 90:
                raise _Invalid('Rotation must be a multiple of 90 degrees.')
            action = options.get('action', 'copy')
            if action not in ('copy', 'optimize', 'encrypt', 'decrypt', 'fill', 'annotate', 'rasterize'):
                raise _Invalid('Unsupported PDF action.')
            if action == 'rasterize':
                writer = PdfWriter()
                for index in selected:
                    with _render(source, password, index, dpi) as image, BytesIO() as buffer:
                        image.save(buffer, format='PDF', resolution=dpi, quality=quality)
                        buffer.seek(0)
                        writer.append(PdfReader(buffer), import_outline=False)
                for page in writer.pages:
                    if rotation:
                        page.rotate(rotation % 360)
                result['dpi'] = dpi
                warnings.append('Rasterization loses selectable text, editable forms, annotations and vector fidelity; stored appearances only, not guaranteed form appearance.')
            else:
                writer = _copy(reader, selected, rotation)
            if action == 'annotate':
                from pypdf.annotations import Text
                text = options.get('annotation')
                if not isinstance(text, str) or not text.strip() or len(text) > 10_000:
                    raise _Invalid('Annotation must contain 1 to 10000 characters of text.')
                index = _page(options.get('page', 0), len(writer.pages))
                box = writer.pages[index].cropbox
                x, y = float(box.left), float(box.bottom)
                writer.add_annotation(index, Text(rect=(x, y, x + 24, y + 24), text=text))
                warnings.append('Text note added to the selected output page; viewer appearance may vary.')
            if action == 'optimize':
                for page in writer.pages:
                    page.compress_content_streams()
                warnings.append('Lossless content-stream compression does not guarantee a smaller file; images are not downsampled.')
            if action == 'fill':
                _fill(writer, options.get('fields'))
                warnings.append('Only ordinary text and checkbox fields are filled; verify font glyphs and field appearance in a viewer.')
            if action == 'encrypt':
                output_password = options.get('output_password', '')
                if not isinstance(output_password, str) or not output_password:
                    raise _Invalid('Provide a nonempty output password for AES-256 encryption.')
                writer.encrypt(user_password=output_password, owner_password=output_password, algorithm='AES-256')
            elif action == 'decrypt' and not reader.is_encrypted:
                warnings.append('The input was already unencrypted.')
            if reader.is_encrypted and action != 'encrypt':
                warnings.append('Output is unencrypted; the input password is not retained.')
            writer.write(stream)
            result.update(pages=selected, page_count=len(selected), action=action, encrypted=(action == 'encrypt'))
            if action != 'rasterize':
                warnings.append('Forms and annotations are copied where supported; signatures are invalidated and document-level features may change.')
        else:
            selected = _pages(options, len(reader.pages))
            texts = [reader.pages[index].extract_text() or '' for index in selected]
            stream.write('\n\f\n'.join(texts).encode('utf-8'))
            result.update(pages=selected, page_count=len(selected), characters=sum(map(len, texts)))
            warnings.append('Text extraction loses layout and images; scanned pages require OCR.')
            if not any(text.strip() for text in texts):
                warnings.append('No selectable text was found. Try OCR for scanned pages.')
    result['after_bytes'] = result['bytes'] = Path(output).stat().st_size
    result['size_change_bytes'] = result['after_bytes'] - result['before_bytes']
    return result


def _geometry(page):
    media = [float(value) for value in page.mediabox]
    crop = [float(value) for value in page.cropbox]
    unit = float(page.get('/UserUnit', 1))  # UserUnit is page-local, not inheritable.
    rotation = float(page.get('/Rotate', 0))
    if (not all(math.isfinite(value) for value in media + crop + [unit, rotation])
            or not 0 < unit <= 75000 or rotation % 90
            or any(box[2] <= box[0] or box[3] <= box[1] for box in (media, crop))):
        raise _Invalid('PDF page geometry is invalid.')
    visible = [max(media[0], crop[0]), max(media[1], crop[1]),
               min(media[2], crop[2]), min(media[3], crop[3])]
    width, height = (visible[2] - visible[0]) * unit, (visible[3] - visible[1]) * unit
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise _Invalid('PDF page geometry is invalid.')
    rotation = int(rotation) % 360
    if rotation in (90, 270):
        width, height = height, width
    return {'width': width, 'height': height, 'mediabox': media, 'cropbox': crop,
            'visiblebox': visible, 'user_unit': unit, 'rotation': rotation}


def _bounded_info(mapping, fields=False):
    result, used, truncated = {}, 0, False
    for index, (key, value) in enumerate(mapping.items()):
        if index >= 100:
            truncated = True
            break
        key = str(key)
        # Do not return shortened field identifiers that could target another field.
        if len(key) > 512:
            truncated = True
            continue
        if fields:
            text = str(value.get('/FT', ''))
            entry = {'type': text[:32]}
            truncated |= len(text) > 32
        else:
            text = str(value)
            entry = text[:2048]
            truncated |= len(text) > 2048
        size = len(json.dumps({key: entry}).encode('utf-8'))
        if used + size > 200_000:
            truncated = True
            break
        result[key] = entry
        used += size
    return result, truncated


@_safe
def inspect(path: str, password: str = '') -> dict:
    """Bounded JSON metadata and visible rotated geometry in physical points.

    Raw media/crop boxes remain in canvas units; width/height use their
    intersection, page-local UserUnit, and displayed rotation. Metadata and
    fields each have a 200KB/100-entry budget. Long field names are omitted,
    never shortened; truncation is reported. No sanitizer guarantee.
    """
    with _reader(path, password) as reader:
        pages = []
        for index, page in enumerate(reader.pages):
            pages.append({'index': index, **_geometry(page),
                          'annotations': len(page.get('/Annots', []))})
        fields, fields_cut = _bounded_info(reader.get_fields() or {}, fields=True)
        metadata, metadata_cut = _bounded_info(reader.metadata or {})
        warnings = [BASE_WARNING]
        if fields_cut or metadata_cut:
            warnings.append('Inspection metadata or field list was truncated to the display budget; long field names are omitted.')
        return {'page_count': len(pages), 'pages': pages, 'fields': fields,
                'metadata': metadata,
                'encrypted': reader.is_encrypted, 'bytes': Path(path).stat().st_size,
                'warnings': warnings}
