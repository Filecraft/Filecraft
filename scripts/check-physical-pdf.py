"""Independent MuPDF gate for physical points, crop intersection and rotation."""
from pathlib import Path
import tempfile,subprocess,json
import fitz
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    script="""
const L=require('./pdf/vendor/pdf-lib.min.js'),P=require('./pdf/document.js'),fs=require('fs');
(async()=>{const d=await L.PDFDocument.create();const a=d.addPage([100,200]);a.node.set(L.PDFName.of('UserUnit'),L.PDFNumber.of(2));d.addPage([300,400]).setCropBox(0,0,300,100);d.addPage([300,400]).setCropBox(-20,-30,120,130);const b=await d.save();const r=await P.transformVerified([b],[{source:0,page:0,rotation:90},{source:0,page:1,rotation:0},{source:0,page:2,rotation:0}]);fs.writeFileSync(process.argv[1]+'/out.pdf',r.bytes);fs.writeFileSync(process.argv[1]+'/info.json',JSON.stringify(r.info));})().catch(e=>{console.error(e);process.exit(1)});
"""
    subprocess.run(['node','-e',script,tmp],cwd=ROOT,check=True)
    info=json.loads((Path(tmp)/'info.json').read_text())
    with fitz.open(Path(tmp)/'out.pdf') as document:
        assert len(document)==3
        for page,data in zip(document,info['pages']):
            expected=(data['height'],data['width']) if data['rotation']%180 else (data['width'],data['height'])
            assert (page.rect.width,page.rect.height)==expected, (page.rect,expected)
            page.get_pixmap(matrix=fitz.Matrix(.25,.25))
    print('PASS independent visible physical geometry: UserUnit, CropBox, clipped CropBox, rotation')
