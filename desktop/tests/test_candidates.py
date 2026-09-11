"""Synthetic PDF auto-fit fixtures; no network or private documents."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from prepare_suite.core import execute


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'private-source.pdf'
        self.output = Path(self.temp.name) / 'result.pdf'
        document = canvas.Canvas(str(self.source), pagesize=(200, 300), pageCompression=0)
        document.drawString(10, 100, 'Synthetic retained text')
        document.showPage()
        document.save()

    def request(self, maximum=None, **rules):
        return {'source': str(self.source), 'output': str(self.output), 'target': 'pdf',
                'options': {'action': 'fit'}, 'profile': {'version': 1, 'id': 'fit-test',
                'constraints': {'bytes': {'max': maximum if maximum is not None else self.source.stat().st_size}, **rules}}}

    def redundant_pdf(self):
        document = canvas.Canvas(str(self.source), pagesize=(200, 300), pageCompression=0)
        for index in range(2):
            document.drawString(10, 100, 'Synthetic retained text ' + str(index))
            for _ in range(2000):
                document.line(10, 20, 100, 200)
            document.showPage()
        document.save()

    def test_structural_candidate_meets_limit_and_retains_text_geometry(self):
        self.redundant_pdf()
        original = self.source.read_bytes()
        result = execute(self.request(5000, pageCount={'min': 2, 'max': 2}, formats=['pdf']))
        self.assertLessEqual(result['bytes'], 5000)
        self.assertLessEqual(result['bytes'], len(original))
        self.assertEqual(self.source.read_bytes(), original)
        before, after = PdfReader(self.source), PdfReader(self.output)
        self.assertEqual([p.extract_text() for p in before.pages], [p.extract_text() for p in after.pages])
        self.assertEqual([list(p.mediabox) for p in before.pages], [list(p.mediabox) for p in after.pages])
        evidence = result['receipt']['candidates']
        self.assertEqual(evidence['selected'], 'structural-optimize')
        self.assertEqual([a['status'] for a in evidence['attempts']], ['rejected', 'passed'])
        self.assertIn({'code': 'textRetention', 'state': 'pass'}, evidence['attempts'][1]['checks'])
        self.assertIn({'code': 'pageGeometry', 'state': 'pass'}, evidence['attempts'][1]['checks'])
        self.assertIn('pypdf', evidence['attempts'][1]['engine'])

    def test_fit_requires_maximum_and_rejects_incompatible_exports(self):
        for options in ({'pages': [0]}, {'rotation': 90}, {'quality': 85}, {'dpi': 72},
                        {'page': 0}, {'fields': {}}, {'output_password': 'secret'},
                        {'password': 'secret'}, {'annotation': 'note'}, {'unknown': True}):
            with self.subTest(options=options):
                request = self.request()
                request['options'].update(options)
                with self.assertRaisesRegex(ValueError, 'Auto-fit'):
                    execute(request)
                self.assertFalse(self.output.exists())
        for profile in (None, {'version': 1, 'id': 'missing-max', 'constraints': {'bytes': {'min': 1}}}):
            request = self.request()
            if profile is None:
                del request['profile']
            else:
                request['profile'] = profile
            with self.assertRaisesRegex(ValueError, 'maximum bytes'):
                execute(request)
        request = self.request()
        request.update(target='txt', output=str(self.output.with_suffix('.txt')))
        with self.assertRaisesRegex(ValueError, 'PDF-to-PDF'):
            execute(request)
        from PIL import Image
        image = self.source.with_suffix('.png')
        Image.new('RGB', (10, 10)).save(image)
        request = self.request()
        request['source'] = str(image)
        with self.assertRaisesRegex(ValueError, 'PDF-to-PDF'):
            execute(request)
        request = self.request()
        request['options'].update(rotation=0, password='')
        execute(request)
        self.assertEqual(self.output.read_bytes(), self.source.read_bytes())

    def test_encrypted_and_signature_fields_refused_before_candidate_write(self):
        from pypdf.generic import DictionaryObject, NameObject, ArrayObject
        for kind in ('encrypted', 'signature', 'unnamed-signature', 'annotation-signature', 'indirect-signature'):
            with self.subTest(kind=kind):
                writer = PdfWriter()
                page = writer.add_blank_page(width=200, height=300)
                if kind == 'encrypted':
                    writer.encrypt('')
                else:
                    field = DictionaryObject({NameObject('/FT'): NameObject('/Sig')})
                    if kind == 'indirect-signature':
                        field[NameObject('/FT')] = writer._add_object(NameObject('/Sig'))
                    ref = writer._add_object(field)
                    if kind == 'annotation-signature':
                        page[NameObject('/Annots')] = ArrayObject([ref])
                    else:
                        if kind == 'signature':
                            from pypdf.generic import TextStringObject
                            field[NameObject('/T')] = TextStringObject('Synthetic signature')
                        writer.root_object[NameObject('/AcroForm')] = writer._add_object(
                            DictionaryObject({NameObject('/Fields'): ArrayObject([ref])}))
                writer.write(self.source)
                original = self.source.read_bytes()
                with patch('prepare_suite.candidates.shutil.copyfile') as copy:
                    with self.assertRaisesRegex(ValueError, 'encrypted|signature'):
                        execute(self.request(100000))
                    copy.assert_not_called()
                self.assertFalse(self.output.exists())
                self.assertEqual(self.source.read_bytes(), original)

    def test_impossible_limit_fails_clearly_without_output(self):
        with self.assertRaisesRegex(ValueError, 'No tested candidate met these requirements'):
            execute(self.request(1))
        self.assertFalse(self.output.exists())
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.source])

    def test_size_regression_rejected_even_if_full_profile_passes(self):
        size = self.source.stat().st_size
        request = self.request(size + 1000)
        request['profile']['constraints']['bytes']['min'] = size + 1
        def inflate(source, output):
            Path(output).write_bytes(Path(source).read_bytes() + b'\n% padding' * 10)
        with patch('prepare_suite.candidates._optimize', side_effect=inflate):
            with self.assertRaisesRegex(ValueError, 'No tested candidate'):
                execute(request)
        self.assertFalse(self.output.exists())

    def test_full_profile_unknown_or_failed_constraints_never_publish(self):
        for rules in ({'pageCount': {'min': 2}}, {'formats': ['png']},
                      {'dimensions': {'unit': 'px', 'maxWidth': 1000}},
                      {'orientation': 'landscape'}, {'filename': {'maxLength': 2}}):
            with self.subTest(rules=rules):
                with self.assertRaisesRegex(ValueError, 'No tested candidate'):
                    execute(self.request(100000, **rules))
                self.assertFalse(self.output.exists())

    def test_optimized_text_or_geometry_changes_never_publish(self):
        for kind in ('text', 'geometry', 'count'):
            with self.subTest(kind=kind):
                self.redundant_pdf()
                def damage(source, output):
                    document = canvas.Canvas(str(output), pagesize=(201 if kind == 'geometry' else 200, 300))
                    for index in range(1 if kind == 'count' else 2):
                        document.drawString(10, 100, 'Changed' if kind == 'text' else 'Synthetic retained text ' + str(index))
                        document.showPage()
                    document.save()
                with patch('prepare_suite.candidates._optimize', side_effect=damage):
                    with self.assertRaisesRegex(ValueError, 'No tested candidate'):
                        execute(self.request(5000))
                self.assertFalse(self.output.exists())

    def test_collisions_preserve_existing_files_including_publication_race(self):
        self.output.write_bytes(b'existing')
        with self.assertRaises(FileExistsError):
            execute(self.request())
        self.assertEqual(self.output.read_bytes(), b'existing')
        self.output.unlink()
        real_link = os.link
        def race(source, destination):
            Path(destination).write_bytes(b'competing')
            real_link(source, destination)
        with patch('prepare_suite.core.os.link', side_effect=race):
            with self.assertRaises(FileExistsError):
                execute(self.request())
        self.assertEqual(self.output.read_bytes(), b'competing')

    def test_cli_auto_fit_real_worker_and_required_limit(self):
        root = Path(__file__).resolve().parents[2]
        command = [sys.executable, str(root / 'desktop' / 'launch.py'), 'prepare',
                   str(self.source), '--target', 'pdf', '--output', str(self.output), '--auto-fit']
        def run(extra):
            result = subprocess.run(command + extra, capture_output=True, text=True, timeout=30)
            return result, json.loads(result.stdout)
        process, response = run([])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('maximum bytes', response['error'])
        self.assertFalse(self.output.exists())
        process, response = run(['--max-bytes', str(self.source.stat().st_size)])
        self.assertEqual(process.returncode, 0, response)
        self.assertEqual(self.output.read_bytes(), self.source.read_bytes())
        self.assertEqual(response['result']['receipt']['candidates']['selected'], 'original')
        self.output.unlink()
        self.redundant_pdf()
        profile = Path(self.temp.name) / 'profile.json'
        profile.write_text(json.dumps(self.request(5000)['profile']))
        process, response = run(['--profile', str(profile)])
        self.assertEqual(process.returncode, 0, response)
        self.assertEqual(response['result']['receipt']['candidates']['selected'], 'structural-optimize')
        self.output.unlink()
        process, response = run(['--max-bytes', '1'])
        self.assertEqual(process.returncode, 1)
        self.assertIn('No tested candidate', response['error'])
        self.assertFalse(self.output.exists())

    def test_passing_original_does_not_require_text_extraction_or_optimization(self):
        with patch('prepare_suite.candidates._retention', side_effect=ValueError('unsupported text')):
            with patch('prepare_suite.candidates._optimize') as optimize:
                execute(self.request())
                optimize.assert_not_called()
        self.assertEqual(self.output.read_bytes(), self.source.read_bytes())

    def test_original_is_exact_bytes_and_receipt_identifies_candidate(self):
        original = self.source.read_bytes()
        result = execute(self.request(pageCount={'min': 1, 'max': 1}, formats=['pdf'],
            dimensions={'unit': 'pt', 'minWidth': 200, 'maxWidth': 200}, orientation='portrait',
            filename={'extensions': ['pdf'], 'asciiOnly': True}))
        self.assertEqual(self.output.read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        evidence = result['receipt']['candidates']
        self.assertEqual(evidence['selected'], 'original')
        self.assertEqual(evidence['maxCandidates'], 2)
        self.assertEqual(len(evidence['attempts']), 1)
        self.assertEqual(evidence['attempts'][0]['status'], 'passed')
        self.assertNotIn(str(self.source), json.dumps(result['receipt']))
        self.assertEqual(result['receipt']['readiness']['status'], 'CHECKS_PASSED')
        self.assertFalse(result['receipt']['visualReviewVerified'])


if __name__ == '__main__':
    unittest.main()
