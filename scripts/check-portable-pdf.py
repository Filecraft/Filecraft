"""Independent rendered-output checks. PyMuPDF is test-only, never shipped."""
from pathlib import Path
import fitz
root=Path(__file__).resolve().parents[1]/'build'/'portable-evidence'
files=list(root.glob('*-split.pdf'))
assert len(files)==2, files
for path in files:
    doc=fitz.open(path)
    assert not doc.is_repaired
    assert len(doc)==2
    for i,page in enumerate(doc):
        assert abs(page.rect.width-595.28)<.01 and abs(page.rect.height-841.89)<.01
        pix=page.get_pixmap()
        pixel=pix.pixel(pix.width//2,pix.height//2)
        assert pixel[i*2]>240 and pixel[2-i*2]<20, (path,i,pixel)
        image=page.get_images()[0]
        assert image[2:4]==(300,400), image
        assert not page.get_text()
    print('PASS',path.name,'valid xref, A4, split order, pixels, no upscale')

for path in root.glob('*-gray.pdf'):
    doc=fitz.open(path)
    assert len(doc)==1 and not doc.is_repaired
    page=doc[0]
    assert tuple(page.rect)==(0,0,612,792)
    pix=page.get_pixmap()
    assert pix.pixel(5,5)==(255,255,255)
    for x in [160,450]:
        pixel=pix.pixel(x,396)
        assert max(pixel)-min(pixel)<=2 and max(pixel)<240, pixel
    assert '/GPS' not in path.read_bytes().decode('latin1')
    print('PASS',path.name,'grayscale pixels, white padding and Letter geometry')
