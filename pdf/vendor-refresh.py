"""Maintainer-only: npm pack in temporary storage, never run by production."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

DEST=Path(__file__).resolve().parent/'vendor'
PACKAGES={'pdf-lib':'1.17.1','@pdf-lib/standard-fonts':'1.0.0','@pdf-lib/upng':'1.0.1','pako':'1.0.11','tslib':'1.11.1'}

def refresh():
    DEST.mkdir(exist_ok=True)
    provenance={'upstream':'https://github.com/Hopding/pdf-lib/releases/tag/v1.17.1','method':'npm pack --ignore-scripts in temporary directory; published UMD copied byte-for-byte; npm SHA-512 integrity checked','packages':[]}
    with tempfile.TemporaryDirectory(prefix='prepare-pdf-vendor-') as temp:
        for package,version in PACKAGES.items():
            identity=f'{package}@{version}'
            registry=json.loads(subprocess.check_output(['npm','view',identity,'dist','--json'],text=True,cwd=temp))
            packed=json.loads(subprocess.check_output(['npm','pack',identity,'--ignore-scripts','--json'],text=True,cwd=temp))[0]
            raw=(Path(temp)/packed['filename']).read_bytes()
            integrity='sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode()
            if integrity!=registry['integrity']: raise ValueError('Package integrity mismatch: '+identity)
            record={'name':package,'version':version,'tarball':registry['tarball'],'integrity':integrity,'sha256':hashlib.sha256(raw).hexdigest(),'files':{}}
            with tarfile.open(Path(temp)/packed['filename']) as archive:
                for member in archive.getmembers():
                    leaf=Path(member.name).name.lower()
                    if not member.isfile(): continue
                    output=None
                    if package=='pdf-lib' and member.name=='package/dist/pdf-lib.min.js': output='pdf-lib.min.js'
                    if member.name.count('/')==1 and (leaf.startswith('license') or leaf.startswith('copyright')):
                        output='LICENSE.'+package.split('/')[-1]+('' if leaf.startswith('license') else '.copyright')
                    if output:
                        extracted=archive.extractfile(member)
                        assert extracted is not None
                        data=extracted.read();(DEST/output).write_bytes(data)
                        record['files'][output]=hashlib.sha256(data).hexdigest()
                        if output=='LICENSE.pdf-lib':
                            (DEST/'LICENSE').write_bytes(data)
                            record['files']['LICENSE']=hashlib.sha256(data).hexdigest()
            provenance['packages'].append(record)
    (DEST/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')

if __name__=='__main__': refresh()
