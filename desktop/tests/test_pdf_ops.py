"""Synthetic, offline integration tests for the isolated PDF worker API."""
import importlib
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def fixture(path, count=2, width=300, height=200):
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    for index in range(count):
        page = writer.add_blank_page(width=width + index, height=height)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 24 Tf 20 100 Td (HELLO PDF PAGE {index}) Tj ET'.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_metadata({'/Title': 'Synthetic fixture'})
    writer.write(path)


def form_fixture(path):
    from pypdf.generic import ArrayObject, FloatObject, TextStringObject, NumberObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    writer.add_blank_page(width=301, height=200)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    resources = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/Helv'): writer._add_object(font)})})
    refs = []
    for name, kind, y in [('name', '/Tx', 130), ('agree', '/Btn', 70)]:
        field = DictionaryObject({NameObject('/Type'): NameObject('/Annot'), NameObject('/Subtype'): NameObject('/Widget'),
            NameObject('/FT'): NameObject(kind), NameObject('/T'): TextStringObject(name),
            NameObject('/Rect'): ArrayObject([FloatObject(v) for v in (20, y, 200, y+25)]),
            NameObject('/P'): page.indirect_reference, NameObject('/F'): NumberObject(4),
            NameObject('/DA'): TextStringObject('/Helv 12 Tf 0 g')})
        if kind == '/Tx':
            field[NameObject('/V')] = TextStringObject('')
        else:
            appearances = DictionaryObject()
            for state in ('/Off', '/Yes'):
                stream = DecodedStreamObject()
                stream.set_data(b'0 0 20 20 re S' + (b' 0 0 m 20 20 l S' if state == '/Yes' else b''))
                stream.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Form'),
                               NameObject('/BBox'): ArrayObject([FloatObject(v) for v in (0, 0, 20, 20)])})
                appearances[NameObject(state)] = writer._add_object(stream)
            field[NameObject('/AP')] = DictionaryObject({NameObject('/N'): appearances})
            field[NameObject('/AS')] = NameObject('/Off')
            field[NameObject('/V')] = NameObject('/Off')
        refs.append(writer._add_object(field))
    page[NameObject('/Annots')] = ArrayObject(refs)
    writer._root_object[NameObject('/AcroForm')] = writer._add_object(DictionaryObject({
        NameObject('/Fields'): ArrayObject(refs), NameObject('/DR'): resources,
        NameObject('/DA'): TextStringObject('/Helv 12 Tf 0 g')}))
    writer.write(path)


class PdfOpsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.pdf'
        fixture(self.source)
        self.original = self.source.read_bytes()
        try:
            self.ops = importlib.import_module('prepare_suite.pdf_ops')
        except ModuleNotFoundError:
            self.fail('PDF worker module has not been implemented')

    def output(self, name='out.pdf'):
        path = self.root / name
        path.touch()
        return str(path)

    def tearDown(self):
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_preview_renders_real_pixels_and_caps_dpi(self):
        from PIL import Image, ImageStat
        output = self.output('preview.png')
        self.assertTrue(hasattr(self.ops, 'preview'), 'Preview is missing')
        result = self.ops.preview(str(self.source), output, page=0, dpi=999)
        with Image.open(output) as image:
            self.assertEqual(image.format, 'PNG')
            self.assertEqual(image.size, (834, 556))
            self.assertGreater(ImageStat.Stat(image.convert('L')).stddev[0], 0)
            self.assertEqual(result['width'], image.width)
        self.assertEqual(result['dpi'], 200)
        self.assertTrue(result['warnings'])

    def test_preview_rejects_unsafe_output_and_pixel_budget(self):
        self.assertTrue(hasattr(self.ops, 'preview'), 'Preview is missing')
        with self.assertRaises(ValueError):
            self.ops.preview(str(self.source), str(self.source))
        with self.assertRaises(ValueError):
            self.ops.preview(str(self.source), self.output('bad.png'), page=-1)
        huge = self.root / 'huge.pdf'
        fixture(huge, count=1, width=20000, height=20000)
        with self.assertRaisesRegex(ValueError, 'pixel'):
            self.ops.preview(str(huge), self.output('huge.png'))

    def test_exports_images_and_selected_text(self):
        from PIL import Image
        self.assertTrue(hasattr(self.ops, 'convert'), 'Conversion is missing')
        for target, fmt in [('png', 'PNG'), ('jpg', 'JPEG')]:
            output = self.output('page.' + target)
            result = self.ops.convert(str(self.source), output, target, {'page': 1, 'dpi': 72, 'quality': 80})
            with Image.open(output) as image:
                self.assertEqual(image.format, fmt)
                self.assertEqual(image.size, (301, 200))
            self.assertEqual(result['page'], 1)
        output = self.output('text.txt')
        result = self.ops.convert(str(self.source), output, 'txt', {'pages': [1, 0]})
        text = Path(output).read_text()
        self.assertLess(text.index('PAGE 1'), text.index('PAGE 0'))
        self.assertEqual(result['pages'], [1, 0])

    def test_copy_reorders_rotates_and_keeps_annotation(self):
        from pypdf.annotations import Text
        annotated = self.root / 'annotated.pdf'
        writer = PdfWriter(clone_from=self.source)
        writer.add_annotation(1, Text(rect=(10, 10, 40, 40), text='Synthetic note'))
        writer.write(annotated)
        output = self.output()
        result = self.ops.convert(str(annotated), output, 'pdf', {'pages': [1, 0], 'rotation': 90})
        reader = PdfReader(output)
        self.assertEqual(len(reader.pages), 2)
        self.assertIn('PAGE 1', reader.pages[0].extract_text())
        self.assertEqual(reader.pages[0].rotation, 90)
        self.assertEqual(reader.pages[0]['/Annots'][0].get_object()['/Contents'], 'Synthetic note')
        self.assertEqual(result['page_count'], 2)
        self.assertEqual(result['after_bytes'], Path(output).stat().st_size)
        self.assertEqual(result['before_bytes'], annotated.stat().st_size)

    def test_optimize_deflates_losslessly_and_reports_actual_sizes(self):
        output = self.output()
        result = self.ops.convert(str(self.source), output, 'pdf', {'action': 'optimize'})
        reader = PdfReader(output)
        self.assertEqual(reader.pages[0].extract_text(), PdfReader(self.source).pages[0].extract_text())
        self.assertEqual(reader.pages[0]['/Contents']['/Filter'], '/FlateDecode')
        self.assertEqual(result['before_bytes'], len(self.original))
        self.assertEqual(result['after_bytes'], Path(output).stat().st_size)
        self.assertEqual(result['size_change_bytes'], result['after_bytes'] - result['before_bytes'])
        self.assertTrue(any('guarantee' in w for w in result['warnings']))

    def test_aes_encrypt_password_preview_and_decrypt(self):
        encrypted = self.output('encrypted.pdf')
        result = self.ops.convert(str(self.source), encrypted, 'pdf', {'action': 'encrypt', 'output_password': 'synthetic password'})
        self.assertTrue(result['encrypted'])
        reader = PdfReader(encrypted)
        self.assertTrue(reader.is_encrypted)
        self.assertEqual(reader.trailer['/Encrypt']['/V'], 5)
        with self.assertRaisesRegex(ValueError, 'password'):
            self.ops.inspect(encrypted, 'wrong')
        self.assertTrue(self.ops.inspect(encrypted, 'synthetic password')['encrypted'])
        self.ops.preview(encrypted, self.output('encrypted.png'), password='synthetic password')
        decrypted = self.output('decrypted.pdf')
        self.ops.convert(encrypted, decrypted, 'pdf', {'action': 'decrypt', 'password': 'synthetic password'})
        reader = PdfReader(decrypted)
        self.assertFalse(reader.is_encrypted)
        self.assertIn('HELLO PDF', reader.pages[0].extract_text())
        with self.assertRaisesRegex(ValueError, 'output password'):
            self.ops.convert(str(self.source), self.output('empty-password.pdf'), 'pdf', {'action': 'encrypt'})

    def test_fill_text_checkbox_and_preserve_reordered_form(self):
        source = self.root / 'form.pdf'
        form_fixture(source)
        info = self.ops.inspect(str(source))
        self.assertEqual(info['fields'], {'name': {'type': '/Tx'}, 'agree': {'type': '/Btn'}})
        output = self.output()
        self.ops.convert(str(source), output, 'pdf', {'action': 'fill', 'pages': [1, 0], 'fields': {'name': 'Synthetic Name', 'agree': True}})
        reader = PdfReader(output)
        fields = reader.get_fields()
        self.assertEqual(fields['name']['/V'], 'Synthetic Name')
        self.assertEqual(fields['agree']['/V'], '/Yes')
        self.assertEqual(len(reader.pages[1]['/Annots']), 2)
        self.assertIn('/AP', reader.pages[1]['/Annots'][0].get_object())
        unchecked = self.output('unchecked.pdf')
        self.ops.convert(output, unchecked, 'pdf', {'action': 'fill', 'fields': {'agree': False}})
        self.assertEqual(PdfReader(unchecked).get_fields()['agree']['/V'], '/Off')
        with self.assertRaisesRegex(ValueError, 'field'):
            self.ops.convert(str(source), self.output('unknown.pdf'), 'pdf', {'action': 'fill', 'fields': {'missing': 'x'}})

    def test_adds_real_text_annotation(self):
        output = self.output()
        self.ops.convert(str(self.source), output, 'pdf', {'action': 'annotate', 'page': 1, 'annotation': 'Review this page'})
        annotation = PdfReader(output).pages[1]['/Annots'][0].get_object()
        self.assertEqual(annotation['/Subtype'], '/Text')
        self.assertEqual(annotation['/Contents'], 'Review this page')

    def test_rasterize_rebuilds_selected_pages_as_images(self):
        from PIL import Image, ImageStat
        output = self.output()
        result = self.ops.convert(str(self.source), output, 'pdf',
                                  {'action': 'rasterize', 'pages': [1, 0], 'dpi': 144, 'rotation': 90})
        reader = PdfReader(output)
        self.assertEqual(len(reader.pages), 2)
        self.assertEqual(reader.pages[0].rotation, 90)
        self.assertAlmostEqual(float(reader.pages[0].mediabox.width), 301, delta=0.5)
        for page in reader.pages:
            self.assertFalse(page.extract_text())
            self.assertNotIn('/Annots', page)
            self.assertEqual(len(page.images), 1)
            self.assertGreater(ImageStat.Stat(page.images[0].image.convert('L')).stddev[0], 0)
        self.assertFalse(reader.get_fields())
        self.assertEqual(result['pages'], [1, 0])
        self.assertEqual(result['dpi'], 144)
        self.assertTrue(any(all(word in warning.lower() for word in ('text', 'forms', 'annotations'))
                            for warning in result['warnings']))
        preview = self.output('raster-preview.png')
        self.ops.preview(output, preview, dpi=72)
        with Image.open(preview) as image:
            self.assertEqual(image.size, (200, 301))

    def test_ocr_recognizes_image_only_pages_in_selected_order(self):
        scan = self.output('scan.pdf')
        self.ops.convert(str(self.source), scan, 'pdf', {'action': 'rasterize', 'dpi': 200})
        self.assertFalse(PdfReader(scan).pages[0].extract_text())
        original_scan = Path(scan).read_bytes()
        for target in ('ocr-pdf', 'ocr-txt'):
            with self.subTest(target=target):
                output = self.output(target)
                result = self.ops.convert(scan, output, target, {'pages': [1, 0], 'dpi': 200})
                if target == 'ocr-pdf':
                    reader = PdfReader(output)
                    self.assertEqual(len(reader.pages), 2)
                    self.assertTrue(reader.pages[0].images)
                    text = '\n'.join(page.extract_text() for page in reader.pages)
                else:
                    text = Path(output).read_text()
                    self.assertIn('\f', text)
                text = ' '.join(text.split())
                self.assertIn('HELLO PDF PAGE 1', text)
                self.assertLess(text.index('PAGE 1'), text.index('PAGE 0'))
                self.assertGreater(result['characters'], 0)
                self.assertEqual(result['pages'], [1, 0])
                self.assertEqual(result['language'], 'eng')
                self.assertTrue(any('OCR' in w for w in result['warnings']))
        self.assertEqual(Path(scan).read_bytes(), original_scan)

    def test_visible_geometry_respects_crop_userunit_and_rotation(self):
        from pypdf.generic import RectangleObject, FloatObject
        from PIL import Image
        source = self.root / 'geometry.pdf'
        writer = PdfWriter(clone_from=self.source)
        page = writer.pages[0]
        page.cropbox = RectangleObject((-10, 20, 250, 180))
        page[NameObject('/UserUnit')] = FloatObject(2)
        page.rotate(90)
        writer.write(source)
        info = self.ops.inspect(str(source))['pages'][0]
        self.assertEqual((info['width'], info['height']), (320, 500))
        self.assertEqual(info['mediabox'], [0, 0, 300, 200])
        self.assertEqual(info['cropbox'], [-10, 20, 250, 180])
        self.assertEqual(info['user_unit'], 2)
        output = self.output('geometry.png')
        self.ops.preview(str(source), output, dpi=72)
        with Image.open(output) as image:
            self.assertEqual(image.size, (320, 500))
        for unit, crop in [(0, (0, 0, 100, 100)), (-1, (0, 0, 100, 100)),
                           (1, (400, 0, 500, 100)), (1, (0, 0, 0, 100))]:
            with self.subTest(unit=unit, crop=crop):
                page[NameObject('/UserUnit')] = FloatObject(unit)
                page.cropbox = RectangleObject(crop)
                writer.write(source)
                with self.assertRaisesRegex(ValueError, 'geometry'):
                    self.ops.inspect(str(source))

    def test_inspect_bounds_untrusted_metadata_and_field_names(self):
        import json
        from pypdf.generic import ArrayObject, TextStringObject
        source = self.root / 'large-info.pdf'
        writer = PdfWriter(clone_from=self.source)
        writer.add_metadata({'/' + str(i) + '界' * 200: '界' * 6000 for i in range(150)})
        fields = []
        for index in range(200):
            fields.append(writer._add_object(DictionaryObject({
                NameObject('/T'): TextStringObject(str(index) + '界' * 2000),
                NameObject('/FT'): NameObject('/Tx')})))
        writer.root_object[NameObject('/AcroForm')] = writer._add_object(DictionaryObject({
            NameObject('/Fields'): ArrayObject(fields)}))
        writer.write(source)
        result = self.ops.inspect(str(source))
        self.assertLess(len(json.dumps(result).encode()), 1_000_000)
        self.assertTrue(any('truncat' in warning.lower() for warning in result['warnings']))

    def test_rejects_indirect_xfa_form_safely(self):
        from pypdf.generic import TextStringObject
        source = self.root / 'xfa.pdf'
        form_fixture(source)
        writer = PdfWriter(clone_from=source)
        writer.root_object['/AcroForm'][NameObject('/XFA')] = TextStringObject('synthetic XFA')
        writer.write(source)
        output = self.output()
        with self.assertRaisesRegex(ValueError, 'XFA'):
            self.ops.convert(str(source), output, 'pdf', {'action': 'fill', 'fields': {'name': 'x'}})
        self.assertEqual(Path(output).stat().st_size, 0)

    def test_ocr_safe_failures_timeout_and_private_cleanup(self):
        import subprocess
        from unittest.mock import patch
        secret = 'secret-must-not-appear'
        for options in ({'tesseract': str(self.root / secret)}, {'language': '../' + secret},
                        {'language': 'prepare_missing_language'}):
            with self.subTest(options=options):
                output = self.output('ocr-failed.txt')
                with self.assertRaises(ValueError) as caught:
                    self.ops.convert(str(self.source), output, 'ocr-txt', options)
                self.assertNotIn(secret, str(caught.exception))
                self.assertEqual(Path(output).stat().st_size, 0)
                self.assertFalse(list(self.root.glob('prepare-ocr-*')))
        with patch.object(self.ops.subprocess, 'run', side_effect=subprocess.TimeoutExpired(secret, 60)) as run:
            output = self.output('timeout.txt')
            with self.assertRaisesRegex(ValueError, 'deadline'):
                self.ops.convert(str(self.source), output, 'ocr-txt', {'password': secret})
            self.assertFalse(run.call_args.kwargs['shell'])
            self.assertEqual(run.call_args.kwargs['timeout'], 60)
            self.assertNotIn(secret, run.call_args.args[0])
        self.assertEqual(Path(output).stat().st_size, 0)
        self.assertFalse(list(self.root.glob('prepare-ocr-*')))

    def test_annotation_validation_and_output_order(self):
        output = self.output()
        self.ops.convert(str(self.source), output, 'pdf',
                         {'action': 'annotate', 'pages': [1, 0], 'page': 0, 'annotation': 'Output first'})
        first = PdfReader(output).pages[0]
        self.assertIn('PAGE 1', first.extract_text())
        self.assertEqual(first['/Annots'][0].get_object()['/Contents'], 'Output first')
        for value in ('', ' ', None, 5, 'x' * 10001):
            with self.subTest(value=str(value)[:20]), self.assertRaisesRegex(ValueError, 'Annotation'):
                self.ops.convert(str(self.source), self.output('bad-note.pdf'), 'pdf',
                                 {'action': 'annotate', 'annotation': value})

    def test_page_and_pixel_budgets_apply_to_new_exports(self):
        from pypdf.generic import FloatObject
        large = self.root / 'large.pdf'
        fixture(large, count=101)
        with self.assertRaisesRegex(ValueError, '100 pages'):
            self.ops.inspect(str(large))
        writer = PdfWriter(clone_from=self.source)
        writer.pages[0][NameObject('/UserUnit')] = FloatObject(100)
        writer.write(large)
        for target, options in [('pdf', {'action': 'rasterize'}), ('ocr-pdf', {}), ('ocr-txt', {})]:
            output = self.output('large-' + target)
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'pixel'):
                self.ops.convert(str(large), output, target, options)
            self.assertEqual(Path(output).stat().st_size, 0)
        with self.assertRaisesRegex(ValueError, '100'):
            self.ops.convert(str(self.source), self.output('many.pdf'), 'pdf', {'pages': [0] * 101})

    def test_blank_ocr_reports_absence_of_searchable_text(self):
        blank = self.root / 'blank.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(blank)
        result = self.ops.convert(str(blank), self.output('blank-ocr.pdf'), 'ocr-pdf', {})
        self.assertEqual(result['characters'], 0)
        self.assertTrue(any('no searchable text' in warning for warning in result['warnings']))

    def test_inspect_metadata_and_geometry(self):
        result = self.ops.inspect(str(self.source))
        self.assertEqual(result['page_count'], 2)
        self.assertEqual(result['metadata']['/Title'], 'Synthetic fixture')
        self.assertEqual(result['pages'][0]['width'], 300)
        self.assertEqual(result['pages'][0]['height'], 200)
        self.assertEqual(result['pages'][0]['rotation'], 0)
        self.assertEqual(result['fields'], {})
        self.assertFalse(result['encrypted'])
        self.assertTrue(result['warnings'])


if __name__ == '__main__':
    unittest.main()
