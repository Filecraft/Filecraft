"""End-to-end regressions for document publication and reading order."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from prepare_suite.core import execute


class DocumentRegressionTests(unittest.TestCase):
    def _extract(self, ext, entries):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / ('input.' + ext)
            output = Path(td) / 'output.txt'
            with zipfile.ZipFile(source, 'w') as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            result = execute({'source': str(source), 'output': str(output), 'target': 'txt'})
            return output.read_text(), result['warnings']

    def _office(self, ext):
        folder, main, group, item, prefix, kind = (
            ('ppt', 'presentation', 'sldIdLst', 'sldId', 'slides/slide', 'slide') if ext == 'pptx'
            else ('xl', 'workbook', 'sheets', 'sheet', 'worksheets/sheet', 'worksheet'))
        entries = {}
        for number in (1, 2, 10):
            text = f'Part{number}'
            entries[f'{folder}/{prefix}{number}.xml'] = (
                f'<slide><p>{text}</p></slide>' if ext == 'pptx' else
                f'<worksheet><row><c t="inlineStr"><is><t>{text}</t></is></c></row></worksheet>')
        entries[f'{folder}/{main}.xml'] = (
            f'<{main} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><{group}>'
            + ''.join(f'<{item} r:id="r{n}"/>' for n in (10, 2, 1)) + f'</{group}></{main}>')
        entries[f'{folder}/_rels/{main}.xml.rels'] = (
            '<Relationships>' + ''.join(f'<Relationship Id="r{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{kind}" Target="{prefix}{n}.xml"/>' for n in (1, 2, 10)) + '</Relationships>')
        return entries

    def test_office_relationship_order_overrides_filenames(self):
        for ext in ('pptx', 'xlsx'):
            with self.subTest(ext=ext):
                text, notices = self._extract(ext, self._office(ext))
                self.assertEqual(text.splitlines(), ['Part10', 'Part2', 'Part1'])
                self.assertFalse(any('order metadata' in n for n in notices))

    def _epub(self):
        return {
            'META-INF/container.xml': '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>',
            'OPS/book.opf': '<package><manifest><item id="a" href="chapter2.xhtml" media-type="application/xhtml+xml"/><item id="b" href="chapter10.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>',
            'OPS/chapter2.xhtml': '<html><p>Second</p></html>',
            'OPS/chapter10.xhtml': '<html><p>First</p></html>',
            'OPS/unused.xhtml': '<html><p>Not in spine</p></html>',
        }

    def test_epub_uses_spine_order_and_excludes_unlisted_chapters(self):
        text, notices = self._extract('epub', self._epub())
        self.assertEqual(text.split(), ['Second', 'First'])
        self.assertFalse(any('order metadata' in n for n in notices))

    def test_missing_order_metadata_uses_natural_sort_with_warning(self):
        for ext in ('pptx', 'xlsx', 'epub'):
            with self.subTest(ext=ext):
                entries = ({f'chapter{n}.xhtml': f'<p>Part{n}</p>' for n in (10, 2, 1)}
                           if ext == 'epub' else {k: v for k, v in self._office(ext).items()
                                                 if '/slides/' in k or '/worksheets/' in k})
                text, notices = self._extract(ext, entries)
                self.assertEqual(text.split(), ['Part1', 'Part2', 'Part10'])
                self.assertTrue(any('order metadata' in n and 'natural' in n for n in notices))

    def test_malformed_order_and_paths_never_fall_back(self):
        for ext in ('pptx', 'xlsx', 'epub'):
            original = self._epub() if ext == 'epub' else self._office(ext)
            metadata = ('OPS/book.opf' if ext == 'epub' else
                        'ppt/_rels/presentation.xml.rels' if ext == 'pptx' else 'xl/_rels/workbook.xml.rels')
            token = 'chapter2.xhtml' if ext == 'epub' else 'slides/slide1.xml' if ext == 'pptx' else 'worksheets/sheet1.xml'
            for bad in ('../../../escape.xml', 'https://example.com/a.xml', 'missing.xml', '%2e%2e/%2e%2e/escape.xml'):
                with self.subTest(ext=ext, bad=bad):
                    entries = dict(original)
                    entries[metadata] = entries[metadata].replace(token, bad)
                    with self.assertRaises(ValueError):
                        self._extract(ext, entries)
            with self.subTest(ext=ext, bad='missing metadata'):
                entries = dict(original)
                del entries[metadata]
                with self.assertRaises(ValueError):
                    self._extract(ext, entries)
            with self.subTest(ext=ext, bad='unknown order reference'):
                entries = dict(original)
                order = 'OPS/book.opf' if ext == 'epub' else 'ppt/presentation.xml' if ext == 'pptx' else 'xl/workbook.xml'
                entries[order] = entries[order].replace('idref="a"', 'idref="unknown"').replace('r:id="r10"', 'r:id="unknown"')
                with self.assertRaises(ValueError):
                    self._extract(ext, entries)

    def test_duplicate_archive_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            import warnings
            source = Path(td) / 'input.pptx'
            output = Path(td) / 'output.txt'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(source, 'w') as archive:
                    for _ in range(2):
                        archive.writestr('ppt/slides/slide1.xml', '<slide><p>Ambiguous</p></slide>')
            with self.assertRaises(ValueError):
                execute({'source': str(source), 'output': str(output), 'target': 'txt'})
            self.assertFalse(output.exists())

    def test_office_package_absolute_relationship_targets_are_supported(self):
        for ext in ('pptx', 'xlsx'):
            entries = self._office(ext)
            rels = next(k for k in entries if k.endswith('.rels'))
            folder = 'ppt' if ext == 'pptx' else 'xl'
            entries[rels] = entries[rels].replace('Target="', f'Target="/{folder}/')
            text, _ = self._extract(ext, entries)
            self.assertEqual(text.splitlines(), ['Part10', 'Part2', 'Part1'])

    def test_docx_rejects_xml_forbidden_controls_before_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'input.txt'
            output = Path(td) / 'output.docx'
            for char in ('\x01', '\x0b', '\x0c', '\ufffe', '\uffff'):
                with self.subTest(codepoint=ord(char)):
                    output = Path(td) / f'output-{ord(char)}.docx'
                    source.write_text('before' + char + 'after', encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'XML'):
                        execute({'source': str(source), 'output': str(output), 'target': 'docx'})
                    self.assertFalse(output.exists())
                    self.assertEqual(list(Path(td).glob('.prepare-*')), [])

    def test_pdf_wraps_wide_words_and_long_tokens_within_margins(self):
        from pypdf import PdfReader
        from reportlab.pdfbase.pdfmetrics import stringWidth
        text = ('WWWW ' * 30).strip() + '\n' + 'W' * 230
        text += ''.join('\n' + 'i' * n + ' ' + 'W' * 100 for n in range(1, 20))
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'input.txt'
            output = Path(td) / 'output.pdf'
            source.write_text(text)
            execute({'source': str(source), 'output': str(output), 'target': 'pdf'})
            lines = []
            for page in PdfReader(output).pages:
                lines.extend(page.extract_text().splitlines())
            self.assertEqual(''.join(lines).replace(' ', ''), text.replace(' ', '').replace('\n', ''))
            self.assertGreater(len(lines), 2)
            for line in lines:
                self.assertLessEqual(stringWidth(line, 'PrepareVera', 11), 595 - 40 - 40 + 0.001)


if __name__ == '__main__':
    unittest.main()
