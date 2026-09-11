"""Build a self-contained offline PDF workbench; no runtime fetch/importScripts."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
VERSION=json.loads((ROOT/'product.json').read_text())['version']
HANDLER="""
self.onmessage=async function(event){
 try {
  const d=event.data;let value;
  if(d.op==='inspect') value=await PreparePDF.inspect(d.bytes);
  else if(d.op==='transform') {value=await PreparePDF.transformVerified(d.inputs,d.plan,d.options);}
  else throw Error('Unknown worker operation');
  self.postMessage({value});
 }catch(e){self.postMessage({error:String(e.message||e).slice(0,1000)});}
};
"""
def sync(check=False):
    script=(ROOT/'pdf/vendor/pdf-lib.min.js').read_text(encoding='utf-8')+'\n'+(ROOT/'pdf/document.js').read_text(encoding='utf-8')+'\n'+HANDLER
    payload={'worker-bundle.js':('/* Generated: python3 scripts/package_workbench.py --sync */\nconst PREPARE_WORKER_SOURCE='+json.dumps(script)+';\n').encode(),'document-engine.js':(ROOT/'engine/document-engine.js').read_bytes(),'readiness-ui.js':(ROOT/'portable/readiness-ui.js').read_bytes()}
    for name,data in payload.items():
        p=ROOT/'workbench'/name
        if check:
            assert p.read_bytes()==data,'Stale '+name
        else:p.write_bytes(data)

def main():
    sync('--check' in sys.argv)
    if '--sync' in sys.argv or '--check' in sys.argv:return
    payload={name:(ROOT/'workbench'/name).read_bytes() for name in ['index.html','style.css','app.js','worker-bundle.js','document-engine.js','readiness-ui.js','README.txt']}
    for name in ['LICENSE','NOTICE']:payload[name]=(ROOT/name).read_bytes()
    payload['THIRD-PARTY.txt']=(ROOT/'pdf/THIRD-PARTY.md').read_bytes()
    for source in (ROOT/'pdf/vendor').iterdir():
        if source.name.startswith('LICENSE') or source.name in ('README.md','PROVENANCE.json'):
            payload['vendor/'+source.name]=source.read_bytes()
    output=ROOT/'build'/f'Filecraft-{VERSION}-pdf-workbench.zip';output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo('Filecraft-Workspace/'+name,date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,data)
    assert sum(map(len,payload.values()))<2000000,'Expanded workbench exceeds 2 MB'
    assert output.stat().st_size<1000000,'ZIP exceeds 1 MB'
    with zipfile.ZipFile(output) as z:assert z.testzip() is None
    output.with_suffix('.zip.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
    print(json.dumps({'version':VERSION,'expanded':sum(map(len,payload.values())),'zip':output.stat().st_size,'files':len(payload)}))
if __name__=='__main__':main()
