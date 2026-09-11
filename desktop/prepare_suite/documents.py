"""Text-first document conversions. Does not execute macros or fetch resources."""
from pathlib import Path
import csv
import html
from html.parser import HTMLParser
import io
import json
import posixpath
import re
from urllib.parse import unquote, urlsplit
import zipfile
from defusedxml import ElementTree as ET

TEXT_INPUTS={'.txt','.md','.markdown','.csv','.tsv','.json','.xml','.html','.htm','.log','.yaml','.yml','.ini','.toml','.rst'}
OFFICE_INPUTS={'.docx','.odt','.pptx','.odp','.xlsx','.ods','.epub'}
TARGETS=['txt','md','html','pdf','docx']
MAX_TEXT=2_000_000

class PlainHTML(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag in ('br','p','div','li','h1','h2','tr'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style') and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def _pdf_lines(line, font, size, width):
    """Wrap at word boundaries, splitting oversized tokens by glyph width."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    widths = {}
    pending = ''
    used = 0
    for char in line.expandtabs(8):
        if char not in widths:
            widths[char] = stringWidth(char, font, size)
        advance = widths[char]
        if pending and used + advance > width:
            boundary = max((i for i, c in enumerate(pending) if c.isspace()), default=-1)
            if boundary > 0:
                yield pending[:boundary]
                pending = pending[boundary + 1:]
            else:
                yield pending
                pending = ''
            used = sum(widths[c] for c in pending)
        pending += char
        used += advance
    if pending or not line:
        yield pending


def _local(node):
    return node.tag.rsplit('}', 1)[-1]


def _part(archive, base, target, package_absolute=False):
    """Resolve package-relative URIs without reading outside the ZIP."""
    if not target or any(ord(c) < 32 for c in target):
        raise ValueError('Invalid document relationship path.')
    uri = urlsplit(target)
    if uri.scheme or uri.netloc or uri.query or uri.fragment:
        raise ValueError('Invalid document relationship path.')
    path = unquote(uri.path, errors='strict')
    if '\\' in path or '\x00' in path or ':' in path:
        raise ValueError('Invalid document relationship path.')
    if package_absolute and path.startswith('/'):
        base, path = '', path[1:]
    name = posixpath.normpath(posixpath.join(posixpath.dirname(base), path))
    if name.startswith(('/', '../')) or name in ('.', '..') or name not in archive.namelist():
        raise ValueError('Missing or unsafe document relationship target.')
    return name


def _office_order(archive, ext):
    folder, main, group, item, kind = (
        ('ppt', 'presentation', 'sldIdLst', 'sldId', 'slide') if ext == '.pptx'
        else ('xl', 'workbook', 'sheets', 'sheet', 'worksheet'))
    document = f'{folder}/{main}.xml'
    relationships = f'{folder}/_rels/{main}.xml.rels'
    if document not in archive.namelist() and relationships not in archive.namelist():
        return None
    if document not in archive.namelist() or relationships not in archive.namelist():
        raise ValueError('Incomplete document order metadata.')
    root = ET.fromstring(archive.read(document))
    groups = [node for node in root if _local(node) == group]
    if len(groups) != 1:
        raise ValueError('Invalid document order metadata.')
    rels = {}
    for node in ET.fromstring(archive.read(relationships)):
        rid = node.get('Id')
        if not rid or rid in rels:
            raise ValueError('Invalid or duplicate relationship ID.')
        rels[rid] = node
    names = []
    seen = set()
    for node in groups[0]:
        ids = [v for k, v in node.attrib.items() if k.endswith('}id')]
        if _local(node) != item or len(ids) != 1 or ids[0] not in rels or ids[0] in seen:
            raise ValueError('Invalid document reading order.')
        seen.add(ids[0])
        rel = rels[ids[0]]
        if rel.get('TargetMode', 'Internal') != 'Internal' or rel.get('Type', '').rsplit('/', 1)[-1] != kind:
            raise ValueError('Unsupported document relationship.')
        name = _part(archive, document, rel.get('Target'), package_absolute=True)
        if name in names:
            raise ValueError('Duplicate document reading-order target.')
        names.append(name)
    return names


def _epub_order(archive):
    container = 'META-INF/container.xml'
    if container not in archive.namelist():
        if any(n.endswith('.opf') for n in archive.namelist()):
            raise ValueError('Incomplete EPUB order metadata.')
        return None
    rootfiles = [n for n in ET.fromstring(archive.read(container)).iter() if _local(n) == 'rootfile']
    if len(rootfiles) != 1:
        raise ValueError('Ambiguous or missing EPUB package.')
    package = _part(archive, '', rootfiles[0].get('full-path'))
    root = ET.fromstring(archive.read(package))
    manifests = [n for n in root if _local(n) == 'manifest']
    spines = [n for n in root if _local(n) == 'spine']
    if len(manifests) != 1 or len(spines) != 1:
        raise ValueError('Invalid EPUB order metadata.')
    items = {}
    for node in manifests[0]:
        key = node.get('id')
        if _local(node) != 'item' or not key or key in items:
            raise ValueError('Invalid EPUB manifest ID.')
        items[key] = node
    names = []
    for node in spines[0]:
        key = node.get('idref')
        if _local(node) != 'itemref' or key not in items:
            raise ValueError('Invalid EPUB spine reference.')
        item = items[key]
        if item.get('media-type') not in ('application/xhtml+xml', 'text/html'):
            raise ValueError('Unsupported EPUB spine content.')
        name = _part(archive, package, item.get('href'))
        if name in names:
            raise ValueError('Duplicate EPUB spine target.')
        names.append(name)
    return names


def _fallback_order(names, notices):
    # Older text-only packages (including minimal fixtures) omit ALL ordering
    # metadata. They remain readable, but inferred order must be disclosed.
    notices.append('Document order metadata absent; using natural filename order, which may differ from reading order.')
    def key(name):
        return ([int(p) if p.isdigit() else p for p in re.split(r'([0-9]+)', name)], name)
    return sorted(names, key=key)


def read_text(source, notices=None):
    if notices is None:notices=[]
    path=Path(source);ext=path.suffix.lower()
    if ext in OFFICE_INPUTS:
        parts=[]
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist()
            if len({i.filename for i in infos}) != len(infos):
                raise ValueError('Duplicate document archive members are ambiguous.')
            if len(infos)>4000 or sum(i.file_size for i in infos)>20_000_000:
                raise ValueError('Office archive exceeds safe expansion limit.')
            if ext=='.docx':names=['word/document.xml']
            elif ext in ('.odt','.ods','.odp'):names=['content.xml']
            elif ext=='.pptx':
                names=_office_order(archive,ext)
                if names is None:names=_fallback_order((n for n in archive.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')),notices)
            elif ext=='.xlsx':
                names=_office_order(archive,ext)
                if names is None:names=_fallback_order((n for n in archive.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')),notices)
                shared=[]
                if 'xl/sharedStrings.xml' in archive.namelist():
                    shared=[''.join(node.itertext()) for node in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
            else:
                names=_epub_order(archive)
                if names is None:names=_fallback_order((n for n in archive.namelist() if n.endswith(('.xhtml','.html','.htm'))),notices)
            for name in names:
                data=archive.read(name)
                if ext=='.epub':
                    parser=PlainHTML();parser.feed(data.decode('utf-8'));parts.append(''.join(parser.parts))
                elif ext=='.xlsx':
                    root=ET.fromstring(data)
                    for row in root.iter():
                        if row.tag.rsplit('}',1)[-1]!='row':continue
                        cells=[]
                        for cell in row:
                            kind=cell.get('t','');value=''
                            for node in cell.iter():
                                local=node.tag.rsplit('}',1)[-1]
                                if local=='v':value=node.text or ''
                                elif local=='t' and kind=='inlineStr':value+=node.text or ''
                            if kind=='s':
                                index=int(value)
                                if index<0 or index>=len(shared):raise ValueError('Invalid shared string index.')
                                value=shared[index]
                            cells.append(value)
                        parts.append('\t'.join(cells))
                else:
                    root=ET.fromstring(data)
                    paragraphs=[]
                    for elem in root.iter():
                        local=elem.tag.rsplit('}',1)[-1]
                        if local in ('p','h','table-row'):
                            paragraphs.append(''.join(elem.itertext()))
                        elif ext=='.xlsx' and local in ('t','v'):paragraphs.append(elem.text or '')
                    parts.extend(paragraphs)
        text='\n'.join(parts)
    else:
        if path.stat().st_size>MAX_TEXT:raise ValueError('Text input exceeds 2 MB.')
        text=path.read_text(encoding='utf-8-sig')
        if '\x00' in text:raise ValueError('Not a supported UTF-8 text file.')
        if ext in ('.html','.htm'):
            parser=PlainHTML();parser.feed(text);text=''.join(parser.parts)
    if not text.strip():raise ValueError('No supported text content found.')
    if len(text)>MAX_TEXT:raise ValueError('Extracted text exceeds 2 million characters.')
    return text

def convert(source,output,target,options):
    extraction_notices=[]
    text=read_text(source, extraction_notices)
    notices=['Text-first conversion: layout, images, macros, comments and interactivity are not preserved. Spreadsheet extraction is not a cell-preserving conversion.']
    notices.extend(extraction_notices)
    if target in ('txt','md'):Path(output).write_text(text,encoding='utf-8')
    elif target=='html':Path(output).write_text('<!doctype html><meta charset="utf-8"><title>Prepared document</title><pre>'+html.escape(text)+'</pre>',encoding='utf-8')
    elif target=='docx':
        # Escape markup only after validating XML 1.0 characters: escaping does
        # not make controls legal, and splitlines would silently discard some.
        if any(not (char in '\t\n\r' or 0x20 <= ord(char) <= 0xD7FF or
                    0xE000 <= ord(char) <= 0xFFFD or 0x10000 <= ord(char) <= 0x10FFFF)
               for char in text):
            raise ValueError('Document contains characters forbidden by XML 1.0.')
        paragraphs=''.join('<w:p><w:r><w:t xml:space="preserve">'+html.escape(line)+'</w:t></w:r></w:p>' for line in text.splitlines())
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+paragraphs+'<w:sectPr/></w:body></w:document>')
    elif target=='pdf':
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import reportlab
        # Bundled Bitstream Vera font; no system fonts or network fetches needed.
        font=Path(reportlab.__file__).parent/'fonts'/'Vera.ttf'
        face=TTFont('PrepareVera',str(font))
        if any(ord(char) not in face.face.charToGlyph for char in text if not char.isspace()):
            raise ValueError('Bundled PDF font lacks characters in this document. Export UTF-8 text or DOCX instead.')
        pdfmetrics.registerFont(face)
        canvas=Canvas(output,pagesize=(595,842));canvas.setFont('PrepareVera',11);y=795;pages=1
        for line in text.splitlines():
            for wrapped in _pdf_lines(line, 'PrepareVera', 11, 595 - 40 - 40):
                if y<45:
                    canvas.showPage();canvas.setFont('PrepareVera',11);y=795;pages+=1
                    if pages>100:raise ValueError('Text produces more than 100 pages.')
                canvas.drawString(40,y,wrapped);y-=15
        canvas.save();notices.append('Bundled font has limited script coverage. Review non-Latin text for missing glyphs.')
    else:raise ValueError('Unsupported text output.')
    return {'warnings':notices}
