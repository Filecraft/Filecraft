import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image

class ConversionTests(unittest.TestCase):
    def test_image_roundtrip_preserves_source_and_exclusive_output(self):
        from prepare_suite.core import execute, capabilities
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'original.png';dst=Path(td)/'copy.jpg'
            Image.new('RGB',(35,22),(210,30,40)).save(src)
            original=hashlib.sha256(src.read_bytes()).digest()
            self.assertIn('jpg',capabilities(str(src))['targets'])
            result=execute({'source':str(src),'output':str(dst),'target':'jpg','options':{}})
            self.assertEqual(result['bytes'],dst.stat().st_size)
            with Image.open(dst) as im:self.assertEqual(im.size,(35,22))
            self.assertEqual(hashlib.sha256(src.read_bytes()).digest(),original)
            with self.assertRaises(FileExistsError):execute({'source':str(src),'output':str(dst),'target':'jpg','options':{}})

class PDFIntegrationTests(unittest.TestCase):
    def test_pdf_dropdown_export_and_password_roundtrip(self):
        from prepare_suite.core import execute,capabilities
        from pypdf import PdfWriter,PdfReader
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.pdf'
            writer=PdfWriter();writer.add_blank_page(width=100,height=200)
            with source.open('wb') as stream:writer.write(stream)
            self.assertIn('pdf',capabilities(source)['targets'])
            png=Path(td)/'preview.png'
            execute({'source':str(source),'output':str(png),'target':'png'})
            with Image.open(png) as image:self.assertGreater(image.height,image.width)
            protected=Path(td)/'protected.pdf'
            execute({'source':str(source),'output':str(protected),'target':'pdf','options':{'action':'encrypt','output_password':'fixture-password'}})
            self.assertTrue(PdfReader(protected).is_encrypted)
            copy=Path(td)/'decrypted.pdf'
            execute({'source':str(protected),'output':str(copy),'target':'pdf','options':{'action':'decrypt','password':'fixture-password'}})
            self.assertFalse(PdfReader(copy).is_encrypted)

class FormatMatrixTests(unittest.TestCase):
    def test_every_advertised_image_output_and_readable_input_roundtrip(self):
        from prepare_suite.core import execute, IMAGE_OUTPUTS
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'source.png';Image.new('RGBA',(64,48),(110,30,220,120)).save(src)
            for target in IMAGE_OUTPUTS:
                with self.subTest(target=target):
                    dst=Path(td)/('out.'+target)
                    execute({'source':str(src),'output':str(dst),'target':target})
                    if target=='pdf':self.assertEqual(len(PdfReader(dst).pages),1)
                    else:
                        back=Path(td)/(target+'-back.png')
                        execute({'source':str(dst),'output':str(back),'target':'png'})
                        with Image.open(back) as im:self.assertGreater(im.width,0)

class BoundaryTests(unittest.TestCase):
    def test_bad_images_and_links_are_rejected_without_output(self):
        import os
        from prepare_suite.core import execute
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'fake.png';src.write_text('not an image')
            dst=Path(td)/'output.jpg'
            with self.assertRaises(Exception):execute({'source':str(src),'output':str(dst),'target':'jpg'})
            self.assertFalse(dst.exists())
            if os.name!='nt':
                link=Path(td)/'link.png';link.symlink_to(src)
                with self.assertRaises(ValueError):execute({'source':str(link),'output':str(dst),'target':'zip'})
            self.assertEqual(list(Path(td).glob('.prepare-*')),[])
    def test_animation_requires_frame_and_selected_frame_exports(self):
        from prepare_suite.core import execute
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'animation.gif';out=Path(td)/'frame.png'
            Image.new('RGB',(20,20),'red').save(src,save_all=True,append_images=[Image.new('RGB',(20,20),'blue')])
            with self.assertRaises(ValueError):execute({'source':str(src),'output':str(out),'target':'png'})
            execute({'source':str(src),'output':str(out),'target':'png','options':{'page':1}})
            with Image.open(out) as im:self.assertEqual(im.convert('RGB').getpixel((0,0)),(0,0,255))

class MediaTests(unittest.TestCase):
    def test_wave_to_flac_and_back(self):
        import shutil, wave
        from prepare_suite.core import execute, capabilities
        if not shutil.which('ffmpeg'):self.skipTest('local FFmpeg not installed')
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'tone.wav'
            with wave.open(str(src),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0\0'*800)
            self.assertIn('flac',capabilities(str(src))['targets'])
            out=Path(td)/'tone.flac';execute({'source':str(src),'output':str(out),'target':'flac'})
            dst=Path(td)/'back.wav';execute({'source':str(out),'output':str(dst),'target':'wav'})
            with wave.open(str(dst),'rb') as w:self.assertEqual(w.getnframes(),800)

class SpreadsheetTests(unittest.TestCase):
    def test_shared_string_cells_are_resolved_not_indices(self):
        import zipfile
        from prepare_suite.core import execute
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'table.xlsx';output=Path(td)/'table.txt'
            with zipfile.ZipFile(source,'w') as z:
                z.writestr('xl/sharedStrings.xml','<sst><si><t>Alice</t></si></sst>')
                z.writestr('xl/worksheets/sheet1.xml','<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c><c r="B1"><v>42</v></c></row></sheetData></worksheet>')
            execute({'source':str(source),'output':str(output),'target':'txt'})
            self.assertEqual(output.read_text().strip(),'Alice\t42')

class StructuredFormatTests(unittest.TestCase):
    def test_text_extraction_for_all_office_containers(self):
        import zipfile
        from prepare_suite.core import execute
        fixtures={'docx':('word/document.xml','<document><p><t>Known content</t></p></document>'),
                  'odt':('content.xml','<document><p>Known content</p></document>'),
                  'ods':('content.xml','<document><table-row><p>Known content</p></table-row></document>'),
                  'odp':('content.xml','<document><p>Known content</p></document>'),
                  'pptx':('ppt/slides/slide1.xml','<slide><p><t>Known content</t></p></slide>'),
                  'epub':('chapter.xhtml','<html><body><p>Known content</p></body></html>')}
        with tempfile.TemporaryDirectory() as td:
            for ext,(name,xml) in fixtures.items():
                with self.subTest(ext=ext):
                    source=Path(td)/('input.'+ext);out=Path(td)/(ext+'.txt')
                    with zipfile.ZipFile(source,'w') as z:z.writestr(name,xml)
                    execute({'source':str(source),'output':str(out),'target':'txt'})
                    self.assertIn('Known content',out.read_text())
    def test_external_entity_archive_is_rejected(self):
        import zipfile
        from prepare_suite.core import execute
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'input.docx';out=Path(td)/'out.txt'
            with zipfile.ZipFile(source,'w') as z:z.writestr('word/document.xml','<!DOCTYPE d [<!ENTITY e SYSTEM "file:///etc/passwd">]><d><p>&e;</p></d>')
            with self.assertRaises(Exception):execute({'source':str(source),'output':str(out),'target':'txt'})
            self.assertFalse(out.exists())

class UnicodeTests(unittest.TestCase):
    def test_pdf_does_not_silently_replace_unsupported_unicode(self):
        from prepare_suite.core import execute
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'unicode.txt';out=Path(td)/'unicode.pdf';source.write_text('你好',encoding='utf-8')
            try:execute({'source':str(source),'output':str(out),'target':'pdf'})
            except ValueError:return
            self.assertIn('你好',PdfReader(out).pages[0].extract_text())

class OutputValidationTests(unittest.TestCase):
    def test_extension_mismatch_is_rejected(self):
        from prepare_suite.core import execute
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'input.png';dst=Path(td)/'misleading.pdf'
            Image.new('RGB',(8,8)).save(src)
            with self.assertRaises(ValueError):execute({'source':str(src),'output':str(dst),'target':'jpg'})
            self.assertFalse(dst.exists())

class DocumentTests(unittest.TestCase):
    def test_text_document_outputs_and_office_roundtrip(self):
        from prepare_suite.core import execute
        from pypdf import PdfReader
        import zipfile
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'notes.txt';src.write_text('Prepare local document\nA readable second line',encoding='utf-8')
            for target in ('pdf','docx','html'):
                dst=Path(td)/('notes.'+target)
                execute({'source':str(src),'output':str(dst),'target':target})
                self.assertGreater(dst.stat().st_size,20)
            self.assertIn('Prepare local document',PdfReader(Path(td)/'notes.pdf').pages[0].extract_text())
            execute({'source':str(Path(td)/'notes.docx'),'output':str(Path(td)/'roundtrip.txt'),'target':'txt'})
            self.assertIn('A readable second line',(Path(td)/'roundtrip.txt').read_text())

class ArchiveTests(unittest.TestCase):
    def test_arbitrary_extension_compression_roundtrip(self):
        import zipfile, gzip
        from prepare_suite.core import execute, capabilities
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'anything.strange-extension';src.write_bytes(bytes(range(256))*400)
            for target in ('zip','gz'):
                self.assertIn(target,capabilities(str(src))['targets'])
                dst=Path(td)/('output.'+target)
                execute({'source':str(src),'output':str(dst),'target':target})
                if target=='zip':
                    with zipfile.ZipFile(dst) as archive:self.assertEqual(archive.read(archive.namelist()[0]),src.read_bytes())
                else:self.assertEqual(gzip.decompress(dst.read_bytes()),src.read_bytes())

if __name__=='__main__':unittest.main()
