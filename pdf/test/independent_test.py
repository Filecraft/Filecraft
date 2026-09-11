"""Optional independent PDFium verification: pip install pypdfium2 (test-only)."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium=None

PDF=Path(__file__).resolve().parents[1]

@unittest.skipIf(pdfium is None,'optional pypdfium2 is not installed')
class IndependentPDFium(unittest.TestCase):
    def test_real_text_render_and_geometry(self):
        assert pdfium is not None
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            script="""
const L=require(process.argv[1]+'/vendor/pdf-lib.min.js');const P=require(process.argv[1]+'/document.js');const fs=require('node:fs');
(async()=>{const d=await L.PDFDocument.create();for(const size of [[210,330],[470,190]]) {const p=d.addPage(size);p.drawText('Prepare actual text',{x:20,y:50,size:12});p.drawRectangle({x:30,y:80,width:41,height:17,color:L.rgb(1,0,0)});}const b=await d.save();fs.writeFileSync(process.argv[2]+'/source.pdf',b);fs.writeFileSync(process.argv[2]+'/out.pdf',await P.transform([b],[{source:0,page:1,rotation:90},{source:0,page:0,rotation:0},{source:0,page:1,rotation:180}],{maxBytes:100000}));})().catch(e=>{console.error(e);process.exitCode=1;});
"""
            run=subprocess.run(['node','-e',script,str(PDF),str(root)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            document=pdfium.PdfDocument(root/'out.pdf')
            self.assertEqual(len(document),3)
            for index,expected in enumerate([(190,470),(210,330),(470,190)]):
                page=document[index]
                self.assertEqual(tuple(page.get_size()),expected)
                text=page.get_textpage();self.assertIn('Prepare actual text',text.get_text_range());text.close()
                bitmap=page.render(scale=0.5);self.assertGreater(len(bitmap.buffer),0)
                # More than one byte value proves this is not a uniform blank image.
                self.assertGreater(len(set(bytes(bitmap.buffer))),2)
                bitmap.close();page.close()
            document.close()

if __name__=='__main__': unittest.main()
