"""Inspect every distributed native file and legal boundary, independently of build."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
results=[]
for arg in sys.argv[1:]:
    p=Path(arg)
    with zipfile.ZipFile(p) as z:
        names=z.namelist();assert z.testzip() is None
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
        assert not any(Path(n).name.lower().startswith('darkgarden') for n in names)
        license_name=next(n for n in names if n.endswith('/licenses/FILECRAFT-LICENSE'))
        assert z.read(license_name)==(ROOT/'LICENSE').read_bytes()
        assert any(n.endswith('/licenses/FILECRAFT-NOTICE') for n in names)
        assert any(n.endswith('Vera.ttf') for n in names)
        assert any(n.endswith('bitstream-vera-license.txt') for n in names)
        source=next(n for n in names if n.endswith('SOURCE-ATTRIBUTION.txt'))
        assert b'SPDX-FileCopyrightText' in z.read(source)
        provenance_name=next(n for n in names if n.endswith('OPENSSL-PROVENANCE.json'))
        prefix=provenance_name.removesuffix('OPENSSL-PROVENANCE.json')
        provenance=json.loads(z.read(provenance_name));assert set(provenance['runtimes'])=={'python','cryptography'}
        for record in provenance['sources']:
            for legal in record['files']:
                body=z.read(prefix+'openssl-'+record['version']+'/'+legal['file'])
                assert hashlib.sha256(body).hexdigest()==legal['sha256']
        natives=[n for n in names if n.lower().endswith(('.dylib','.dll','.so','.pyd')) or '.so.' in n]
        results.append({'archive':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nativeFiles':natives,'openssl':provenance['runtimes'],'licenseBoundary':'Apache-2.0 project; original third-party terms retained','passed':True})
assert results,'Pass archive paths explicitly'
print(json.dumps(results,indent=2))
