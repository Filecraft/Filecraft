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
print('PASS frozen application worker: JPEG, PDF and archive export; independent image/PDF readback')
