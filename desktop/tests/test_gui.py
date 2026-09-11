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
