"""Exercise actual frozen worker and verify produced bytes independently."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image
from pypdf import PdfReader

executable=Path(sys.argv[1]).resolve()
subprocess.run([str(executable),'--check-runtime'],check=True,timeout=60)
with tempfile.TemporaryDirectory() as td:
    folder=Path(td);source=folder/'input.png';Image.new('RGB',(80,60),'navy').save(source)
    for target in ['jpg','pdf','zip']:
        output=folder/('out.'+target)
        request={'source':str(source),'output':str(output),'target':target}
        proc=subprocess.run([str(executable),'--worker'],input=json.dumps(request),text=True,capture_output=True,timeout=60)
        assert proc.returncode==0,(target,proc.stdout,proc.stderr)
        result=json.loads(proc.stdout);assert result['ok'],result
        assert output.stat().st_size==result['result']['bytes']
    assert len(PdfReader(folder/'out.pdf').pages)==1
    with Image.open(folder/'out.jpg') as image:assert image.size==(80,60)
    import hashlib
    proof=folder/'receipt.json';proof.write_text(json.dumps(result['result']['receipt']))
    verified=subprocess.run([str(executable),'verify',str(folder/'out.zip'),'--receipt',str(proof)],capture_output=True,text=True,timeout=60)
    assert verified.returncode==0 and json.loads(verified.stdout)['result']['matches'],verified.stdout
    blocked=folder/'blocked.pdf'
    failed=subprocess.run([str(executable),'prepare',str(source),'--output',str(blocked),'--target','pdf','--max-bytes','1'],capture_output=True,text=True,timeout=60)
    assert failed.returncode==1 and not blocked.exists(),failed.stdout
    source=folder/'out.pdf'
    for target,options in [('png',{}),('pdf',{'action':'encrypt','output_password':'synthetic-password'}),('pdf',{'action':'rasterize'})]:
        output=folder/(options.get('action','preview')+'.'+target)
        proc=subprocess.run([str(executable),'--worker'],input=json.dumps({'source':str(source),'output':str(output),'target':target,'options':options}),text=True,capture_output=True,timeout=60)
        assert proc.returncode==0,(target,proc.stdout,proc.stderr)
        assert json.loads(proc.stdout)['ok'],proc.stdout
        if target=='pdf':
            checked=PdfReader(output)
            if options.get('action')=='encrypt':assert checked.decrypt('synthetic-password')
            assert len(checked.pages)==1
        else:
            with Image.open(output) as image:assert image.width>0
    from reportlab.pdfgen import canvas
    fitting=folder/'fit-source.pdf'
    doc=canvas.Canvas(str(fitting),pageCompression=0)
    doc.drawString(20,100,'Synthetic auto-fit retained text')
    for _ in range(2000):doc.line(10,20,100,200)
    doc.save()
    for name,limit,recipe in [('exact',fitting.stat().st_size,'original'),('fit',5000,'structural-optimize')]:
        out=folder/(name+'.pdf')
        proc=subprocess.run([str(executable),'prepare',str(fitting),'--output',str(out),'--target','pdf','--auto-fit','--max-bytes',str(limit)],capture_output=True,text=True,timeout=60)
        assert proc.returncode==0,(proc.stdout,proc.stderr)
        data=json.loads(proc.stdout)['result'];assert data['receipt']['candidates']['selected']==recipe
        assert data['receipt']['output']['sha256']==hashlib.sha256(out.read_bytes()).hexdigest()
        assert out.stat().st_size<=limit
        if recipe=='original':assert out.read_bytes()==fitting.read_bytes()
        else:assert PdfReader(out).pages[0].extract_text()==PdfReader(fitting).pages[0].extract_text()
print('PASS frozen worker: image/PDF/archive, preview, AES, rasterization and exact/optimized auto-fit')
