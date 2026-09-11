"""Independent renderer gate for browser-generated PDF artifacts. Test-only PyMuPDF."""
from pathlib import Path
import fitz
root=Path(__file__).resolve().parents[1]
files=sorted((root/'build/pdf-workbench-evidence').glob('output-*.pdf'))
assert len(files)==2, f'Expected Chromium and Firefox output, got {files}'
for file in files:
    doc=fitz.open(file)
    assert len(doc)==2
    assert (doc[0].mediabox.width,doc[0].mediabox.height,doc[0].rotation)==(300,400,0)
    assert (doc[1].mediabox.width,doc[1].mediabox.height,doc[1].rotation)==(500,600,90)
    for page in doc:
        pix=page.get_pixmap(matrix=fitz.Matrix(.5,.5))
        assert min(pix.samples)<200, 'Expected real colored marks, not blank pages'
    print('PASS independent PDF parse, geometry, rotation and rendered marks:',file.name)
