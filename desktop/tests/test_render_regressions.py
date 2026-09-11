import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageStat
from pypdf import PdfReader
from test_pdf_ops import form_fixture
from prepare_suite.core import execute

class RenderRegressions(unittest.TestCase):
    def test_filled_widgets_are_visible_in_preview_and_raster(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'form.pdf';filled=root/'filled.pdf';form_fixture(source)
            execute({'source':str(source),'output':str(filled),'target':'pdf','options':{'action':'fill','fields':{'name':'VISIBLE NAME','agree':True}}})
            for target,options in [('png',{}),('pdf',{'action':'rasterize'})]:
                output=root/('visible.'+target)
                execute({'source':str(filled),'output':str(output),'target':target,'options':options})
                if target=='png':
                    with Image.open(output) as image:self.assertGreater(ImageStat.Stat(image.convert('L')).stddev[0],10)
                else:
                    image=PdfReader(output).pages[0].images[0].image
                    self.assertGreater(ImageStat.Stat(image.convert('L')).stddev[0],10)
