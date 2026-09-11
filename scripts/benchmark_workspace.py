"""Machine-local observations, not product speed claims or a competitor ranking."""
from pathlib import Path
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
exe=sys.executable
rows=[]
with tempfile.TemporaryDirectory(prefix='prepare-bench-') as td:
    folder=Path(td);source=folder/'scan.png';Image.new('RGB',(1600,2200),'white').save(source)
    for target in ('pdf','jpg','zip'):
        for trial in range(5):
            output=folder/f'{target}-{trial}.{target}';start=time.perf_counter()
            proc=subprocess.run([exe,str(ROOT/'desktop/launch.py'),'prepare',str(source),'--target',target,'--output',str(output)],capture_output=True,text=True,timeout=180)
            elapsed=time.perf_counter()-start;result=json.loads(proc.stdout)
            assert proc.returncode==0 and result['ok'],proc.stdout
            assert result['result']['sha256']==hashlib.sha256(output.read_bytes()).hexdigest()
            rows.append({'operation':'worker-start+import+transform+validate+hash+publish','target':target,'trial':trial,'seconds':elapsed,'inputBytes':source.stat().st_size,'outputBytes':output.stat().st_size})
    # Same JPEG transform through Pillow alone; deliberately narrower scope.
    for trial in range(5):
        output=folder/f'pillow-{trial}.jpg';start=time.perf_counter()
        proc=subprocess.run([exe,'-c',"from PIL import Image;import sys;Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2],quality=82,optimize=True)",str(source),str(output)],capture_output=True,timeout=60);assert proc.returncode==0
        rows.append({'operation':'Pillow subprocess transform only (not equivalent validation/publication)','target':'jpg','trial':trial,'seconds':time.perf_counter()-start,'outputBytes':output.stat().st_size})
result={'environment':{'os':platform.platform(),'machine':platform.machine(),'python':platform.python_version()},'fixture':'Synthetic flat white RGB scan, 1600×2200; unrepresentative of real compression complexity','limitations':'Warm filesystem; five sequential trials; CLI wall time, not GUI startup or peak memory. Pillow-only baseline lacks Prepare validation, provenance, publication protections. Not a competitive speed ranking.','samples':rows,'medianSeconds':{op+' / '+target:statistics.median(r['seconds'] for r in rows if r['operation']==op and r['target']==target) for op,target in sorted({(r['operation'],r['target']) for r in rows})}}
path=ROOT/'build/v09-benchmark.json';path.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
