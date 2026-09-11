"""Text-first document conversions. Does not execute macros or fetch resources."""
from pathlib import Path
import csv
import html
from html.parser import HTMLParser
import io
import json
import textwrap
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

def read_text(source):
    path=Path(source);ext=path.suffix.lower()
    if ext in OFFICE_INPUTS:
        parts=[]
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist()
            if len(infos)>4000 or sum(i.file_size for i in infos)>20_000_000:
                raise ValueError('Office archive exceeds safe expansion limit.')
            if ext=='.docx':names=['word/document.xml']
            elif ext in ('.odt','.ods','.odp'):names=['content.xml']
            elif ext=='.pptx':names=sorted(n for n in archive.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml'))
            elif ext=='.xlsx':
                names=sorted(n for n in archive.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'))
                shared=[]
                if 'xl/sharedStrings.xml' in archive.namelist():
                    shared=[''.join(node.itertext()) for node in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
            else:names=sorted(n for n in archive.namelist() if n.endswith(('.xhtml','.html','.htm')))
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
    text=read_text(source)
    notices=['Text-first conversion: layout, images, macros, comments and interactivity are not preserved. Spreadsheet extraction is not a cell-preserving conversion.']
    if target in ('txt','md'):Path(output).write_text(text,encoding='utf-8')
    elif target=='html':Path(output).write_text('<!doctype html><meta charset="utf-8"><title>Prepared document</title><pre>'+html.escape(text)+'</pre>',encoding='utf-8')
    elif target=='docx':
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
            for wrapped in textwrap.wrap(line,82,replace_whitespace=False) or ['']:
                if y<45:
                    canvas.showPage();canvas.setFont('PrepareVera',11);y=795;pages+=1
                    if pages>100:raise ValueError('Text produces more than 100 pages.')
                canvas.drawString(40,y,wrapped);y-=15
        canvas.save();notices.append('Bundled font has limited script coverage. Review non-Latin text for missing glyphs.')
    else:raise ValueError('Unsupported text output.')
    return {'warnings':notices}
