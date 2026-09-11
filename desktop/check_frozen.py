"""Exercise actual frozen worker and verify produced bytes independently."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image
from pypdf import PdfReader

executable=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as td:
    folder=Path(td);source=folder/'input.png';Image.new('RGB',(80,60),'navy').save(source)
    for target in ['jpg','pdf','zip']:
        output=folder/('out.'+target)
        request={'source':str(source),'output':str(output),'target':target}
        proc=subprocess.run([str(executable),'--worker'],input=json.dumps(request),text=True,capture_output=True,timeout=60)
        assert proc.returncode==0,(proc.stdout,proc.stderr)
        result=json.loads(proc.stdout);assert result['ok'],result
        assert output.stat().st_size==result['result']['bytes']
    assert len(PdfReader(folder/'out.pdf').pages)==1
    with Image.open(folder/'out.jpg') as image:assert image.size==(80,60)
    source=folder/'out.pdf'
    for target,options in [('png',{}),('pdf',{'action':'encrypt','output_password':'synthetic-password'}),('pdf',{'action':'rasterize'})]:
        output=folder/(options.get('action','preview')+'.'+target)
        proc=subprocess.run([str(executable),'--worker'],input=json.dumps({'source':str(source),'output':str(output),'target':target,'options':options}),text=True,capture_output=True,timeout=60)
        assert proc.returncode==0,(proc.stdout,proc.stderr)
        assert json.loads(proc.stdout)['ok'],proc.stdout
        if target=='pdf':
            checked=PdfReader(output)
            if options.get('action')=='encrypt':assert checked.decrypt('synthetic-password')
            assert len(checked.pages)==1
        else:
            with Image.open(output) as image:assert image.width>0
print('PASS frozen worker: image/PDF/archive exports, PDF preview, AES and rasterization')
