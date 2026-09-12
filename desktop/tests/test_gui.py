import json
import tempfile
import time
import unittest
from pathlib import Path
from PIL import Image

class GUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        cls.root=tk.Tk()
        cls.root.withdraw()
    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
    def tearDown(self):
        for callback in self.root.tk.splitlist(self.root.tk.call('after','info')):
            self.root.after_cancel(callback)
        for widget in self.root.winfo_children():widget.destroy()
    def test_initial_empty_layout_hides_irrelevant_options_and_shows_export(self):
        from prepare_suite.gui import App
        app=App(self.root)
        self.root.deiconify()
        try:
            self.root.update()
            self.assertEqual(app.source,'')
            self.assertEqual(app.target.get(),'')
            self.assertEqual(app.status.get(),'Choose a local file. Originals are never overwritten.')
            self.assertEqual(app.preview_identity.get(),'No preview rendered.')
            visible={'Preview / image page','Image quality (1–95)'}
            for label,widgets in app.option_widgets.items():
                with self.subTest(option=label):
                    for widget in widgets:
                        self.assertEqual(widget.winfo_manager(),'grid' if label in visible else '')
                        self.assertEqual(bool(widget.winfo_ismapped()),label in visible)
            self.assertTrue(app.save_button.winfo_ismapped())
            x=app.save_button.winfo_rootx()-self.root.winfo_rootx()
            y=app.save_button.winfo_rooty()-self.root.winfo_rooty()
            self.assertGreaterEqual(x,0)
            self.assertGreaterEqual(y,0)
            self.assertLessEqual(x+app.save_button.winfo_width(),self.root.winfo_width())
            self.assertLessEqual(y+app.save_button.winfo_height(),self.root.winfo_height())
        finally:
            self.root.withdraw()

    def test_pdf_fit_selection_and_actual_export(self):
        from prepare_suite.gui import App
        from pypdf import PdfWriter
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.pdf';output=Path(td)/'fit.pdf'
            writer=PdfWriter();writer.add_blank_page(width=100,height=200);writer.write(source)
            app.load_source(str(source))
            self.assertIn('fit',app.option_widgets['PDF operation'][1]['values'])
            app.action.set('fit')
            self.assertEqual(app.get_options(),{'password':'','action':'fit','rotation':0})
            app.begin_export(str(output));self.wait_for_job(app)
            self.assertFalse(output.exists());self.assertIn('maximum bytes',app.status.get())
            app.max_bytes.set(str(source.stat().st_size))
            app.pages.set('1');app.begin_export(str(output));self.wait_for_job(app)
            self.assertFalse(output.exists());self.assertIn('Auto-fit',app.status.get())
            app.pages.set('');app.begin_export(str(output));self.wait_for_job(app)
            self.assertEqual(output.read_bytes(),source.read_bytes())
            self.assertEqual(app.last_receipt['candidates']['selected'],'original')

    def test_dropdown_and_actual_async_export(self):
        import tkinter as tk
        from prepare_suite.gui import App
        root=self.root
        try:
            app=App(root)
            with tempfile.TemporaryDirectory() as td:
                source=Path(td)/'source.png';output=Path(td)/'result.jpg'
                Image.new('RGB',(40,30),'green').save(source)
                app.load_source(str(source))
                self.assertIn('jpg',app.target_box['values'])
                app.target.set('jpg');app.begin_export(str(output))
                until=time.monotonic()+20
                while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
                self.assertFalse(app.busy)
                self.assertTrue(output.exists(),app.status.get())
                self.assertIn('Saved',app.status.get())
                self.assertTrue(source.exists())
        finally:pass

    def test_requirements_gate_and_receipt_export(self):
        from prepare_suite.gui import App
        from unittest.mock import patch
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';output=Path(td)/'result.png';receipt=Path(td)/'receipt.json'
            Image.new('RGB',(40,30),'green').save(source)
            app.load_source(str(source));app.max_bytes.set('1')
            app.begin_export(str(output))
            until=time.monotonic()+20
            while app.busy and time.monotonic()<until:self.root.update();time.sleep(.02)
            self.assertFalse(output.exists());self.assertIn('requirements',app.status.get())
            app.max_bytes.set('100000');app.begin_export(str(output))
            until=time.monotonic()+20
            while app.busy and time.monotonic()<until:self.root.update();time.sleep(.02)
            self.assertTrue(output.exists(),app.status.get())
            with patch('prepare_suite.gui.filedialog.asksaveasfilename',return_value=str(receipt)):
                app.save_receipt()
            self.assertEqual(json.loads(receipt.read_text())['readiness']['status'],'CHECKS_PASSED')
            self.assertEqual(app.option_widgets['PDF operation'][1].winfo_manager(),'')

    def wait_for_job(self,app):
        until=time.monotonic()+20
        while app.busy and time.monotonic()<until:self.root.update();time.sleep(.02)
        self.assertFalse(app.busy,app.status.get())

    def test_export_freezes_editable_controls(self):
        from tkinter import ttk
        from prepare_suite.gui import App
        app=App(self.root)
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        controls=[w for w in descendants(self.root) if isinstance(w,ttk.Entry) or
                  isinstance(w,ttk.Button) and w.cget('text') in ('Import profile…','Clear requirements')]
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';output=Path(td)/'result.png'
            Image.new('RGB',(40,30),'green').save(source)
            app.load_source(str(source));app.max_bytes.set('10000')
            app.begin_export(str(output))
            try:
                self.assertTrue(app.busy)
                for widget in controls:self.assertTrue(widget.instate(['disabled']),str(widget))
                app.clear_requirements()
                self.assertEqual(app.max_bytes.get(),'10000')
            finally:self.wait_for_job(app)
            for widget in controls:self.assertFalse(widget.instate(['disabled']),str(widget))
            self.assertTrue(app.target_box.instate(['readonly']))
            self.assertTrue(output.exists(),app.status.get())

    def test_configuration_edits_invalidate_export(self):
        from prepare_suite.gui import App
        from unittest.mock import patch
        app=App(self.root)
        variables=('max_bytes','max_pages','target','action','pages','rotation','page','dpi',
                   'quality','password','output_password','language','annotation','fields')
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png'
            Image.new('RGB',(40,30),'green').save(source)
            app.load_source(str(source))
            for index,name in enumerate(variables):
                with self.subTest(variable=name):
                    output=Path(td)/f'result-{index}.png'
                    app.begin_export(str(output));self.wait_for_job(app)
                    self.assertIsNotNone(app.last_receipt,app.status.get())
                    original=output.read_bytes()
                    var=getattr(app,name);value=var.get();var.set(value+'x')
                    try:
                        self.assertIsNone(app.last_receipt)
                        self.assertEqual(app.output,'')
                        self.assertTrue(app.receipt_button.instate(['disabled']))
                        self.assertNotIn('CHECKS_PASSED',app.status.get())
                        with patch('prepare_suite.gui.filedialog.asksaveasfilename') as dialog:
                            app.save_receipt();dialog.assert_not_called()
                        self.assertEqual(output.read_bytes(),original)
                    finally:var.set(value)

    def test_replacement_export_failure_invalidates_previous_receipt(self):
        from prepare_suite.gui import App
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';output=Path(td)/'result.png'
            Image.new('RGB',(40,30),'green').save(source)
            app.load_source(str(source));app.begin_export(str(output));self.wait_for_job(app)
            original=output.read_bytes()
            app.begin_export(str(output))
            try:
                self.assertIsNone(app.last_receipt)
                self.assertEqual(app.output,'')
            finally:self.wait_for_job(app)
            self.assertIn('existing files',app.status.get())
            self.assertIsNone(app.last_receipt)
            self.assertTrue(app.receipt_button.instate(['disabled']))
            self.assertEqual(output.read_bytes(),original)

    def test_inflight_configuration_edit_cannot_publish_stale_receipt(self):
        from prepare_suite.gui import App
        from pypdf import PdfWriter
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.pdf';output=Path(td)/'result.pdf'
            writer=PdfWriter();writer.add_blank_page(width=100,height=200)
            with source.open('wb') as stream:writer.write(stream)
            app.load_source(str(source));app.max_bytes.set('10000')
            app.begin_export(str(output));app.max_bytes.set('1');self.wait_for_job(app)
            self.assertTrue(output.exists(),app.status.get())
            self.assertIsNone(app.last_receipt)
            self.assertEqual(app.output,'')
            self.assertNotIn('CHECKS_PASSED',app.status.get())
            self.assertTrue(app.receipt_button.instate(['disabled']))

    def test_replacement_validation_failure_invalidates_previous_receipt(self):
        from prepare_suite.gui import App
        from unittest.mock import patch
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';output=Path(td)/'result.png'
            Image.new('RGB',(40,30),'green').save(source)
            app.load_source(str(source));app.begin_export(str(output));self.wait_for_job(app)
            original=output.read_bytes()
            with patch.object(app,'get_options',side_effect=ValueError('Invalid options')):
                app.begin_export(str(Path(td)/'replacement.png'))
            self.assertFalse(app.busy)
            self.assertEqual(app.status.get(),'Invalid options')
            self.assertIsNone(app.last_receipt)
            self.assertEqual(app.output,'')
            self.assertTrue(app.receipt_button.instate(['disabled']))
            self.assertEqual(output.read_bytes(),original)

    def test_profile_import_and_clear_invalidate_receipt(self):
        from prepare_suite.gui import App
        from unittest.mock import patch
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';output=Path(td)/'result.png';profile=Path(td)/'profile.json'
            Image.new('RGB',(40,30),'green').save(source)
            profile.write_text(json.dumps({'version':1,'id':'test-profile','constraints':{'bytes':{'max':10000}}}))
            app.load_source(str(source));app.begin_export(str(output));self.wait_for_job(app)
            with patch('prepare_suite.gui.filedialog.askopenfilename',return_value=str(profile)):
                app.import_profile()
            self.assertEqual(app.profile['id'],'test-profile')
            self.assertIsNone(app.last_receipt)
            self.assertEqual(app.output,'')
            app.begin_export(str(Path(td)/'second.png'));self.wait_for_job(app)
            self.assertIsNotNone(app.last_receipt,app.status.get())
            app.clear_requirements()
            self.assertIsNone(app.last_receipt)
            self.assertEqual(app.output,'')
            self.assertTrue(app.receipt_button.instate(['disabled']))
            self.assertTrue(output.exists())

    def test_hidden_fill_json_does_not_break_copy_or_preview(self):
        from prepare_suite.gui import App
        from pypdf import PdfWriter
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.pdf';output=Path(td)/'copy.pdf'
            writer=PdfWriter();writer.add_blank_page(width=100,height=200)
            with source.open('wb') as stream:writer.write(stream)
            app.load_source(str(source));app.action.set('fill');app.fields.set('{bad json')
            with self.assertRaises(ValueError):app.get_options()
            app.action.set('copy')
            self.assertEqual(app.option_widgets['Form values (JSON object)'][1].winfo_manager(),'')
            app.begin_export(str(output));self.wait_for_job(app)
            self.assertTrue(output.exists(),app.status.get())
            self.assertNotIn('fields',app.get_options())
            app.action.set('fill');app.preview(False);self.wait_for_job(app)
            try:self.assertIsNotNone(app.photo,app.status.get())
            finally:
                if app.preview_dir:app.preview_dir.cleanup()

    def test_only_relevant_options_are_parsed(self):
        from prepare_suite.gui import App
        app=App(self.root)
        app.fields.set('{bad');app.pages.set('bad');app.rotation.set('bad')
        app.dpi.set('bad');app.page.set('bad');app.quality.set('bad')
        for source,target,expected in [('source.pdf','zip',{}),('source.txt','pdf',{}),
                                       ('source.png','png',{'page':0,'quality':85})]:
            with self.subTest(source=source,target=target):
                app.source=source;app.target.set(target)
                if source.endswith('.png'):app.page.set('1');app.quality.set('85')
                self.assertEqual(app.get_options(),expected)
        app.source='source.pdf';app.target.set('pdf');app.pages.set('1');app.rotation.set('90')
        self.assertEqual(app.get_options(),{'password':'','pages':[0],'action':'copy','rotation':90})
        app.action.set('rasterize')
        with self.assertRaises(ValueError):app.get_options()

    def test_preview_page_navigation_preserves_pdf_copy_receipt(self):
        from prepare_suite.gui import App
        from pypdf import PdfWriter
        app=App(self.root)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'two.pdf';output=Path(td)/'copy.pdf'
            writer=PdfWriter();writer.add_blank_page(width=100,height=200);writer.add_blank_page(width=200,height=100)
            with source.open('wb') as stream:writer.write(stream)
            app.load_source(str(source));app.begin_export(str(output));self.wait_for_job(app)
            receipt=app.last_receipt;original=output.read_bytes()
            app.preview(True);self.wait_for_job(app)
            app.page.set('2')
            self.assertEqual(app.output,str(output))
            self.assertIs(app.last_receipt,receipt)
            self.assertIsNone(app.photo)
            app.preview(True);self.wait_for_job(app)
            try:
                self.assertIsNotNone(app.photo,app.status.get())
                self.assertIn('page 2',app.preview_identity.get())
                self.assertIs(app.last_receipt,receipt)
                self.assertEqual(output.read_bytes(),original)
                app.action.set('annotate');app.annotation.set('Synthetic review');app.begin_export(str(Path(td)/'annotated.pdf'));self.wait_for_job(app)
                self.assertIsNotNone(app.last_receipt,app.status.get())
                app.page.set('1');self.assertIsNone(app.last_receipt)
                app.target.set('png');app.begin_export(str(Path(td)/'page.png'));self.wait_for_job(app)
                self.assertIsNotNone(app.last_receipt,app.status.get())
                app.page.set('2');self.assertIsNone(app.last_receipt)
            finally:
                if app.preview_dir:app.preview_dir.cleanup()

    def test_pdf_source_and_output_previews(self):
        import tkinter as tk
        from prepare_suite.gui import App
        from pypdf import PdfWriter
        root=self.root
        try:
            app=App(root)
            with tempfile.TemporaryDirectory() as td:
                source=Path(td)/'source.pdf';output=Path(td)/'rotated.pdf'
                writer=PdfWriter();writer.add_blank_page(width=100,height=200)
                with source.open('wb') as stream:writer.write(stream)
                app.load_source(str(source));app.preview(False)
                until=time.monotonic()+20
                while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
                self.assertIsNotNone(app.photo,app.status.get())
                self.assertIn('source.pdf',app.preview_identity.get())
                self.assertIn('SHA-256',app.preview_identity.get())
                app.target.set('pdf');app.rotation.set('90');app.begin_export(str(output))
                until=time.monotonic()+20
                while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
                self.assertTrue(output.exists(),app.status.get())
                self.assertIsNone(app.photo)
                app.preview(True)
                until=time.monotonic()+20
                while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
                self.assertIn('Preview rendered',app.status.get())
                if app.preview_dir:app.preview_dir.cleanup()
        finally:pass

if __name__=='__main__':unittest.main()
