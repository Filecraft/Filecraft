"""Fail on new-surface version drift; historical product versions are intentional."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/'product.json').read_text());v=p['version']
# The unchanged browser workspace is a separately shipped historical artifact.
# Packaging resolves product.json dynamically rather than duplicating its version.
import runpy
assert runpy.run_path(str(ROOT/'desktop/package.py'))['VERSION']==v
for name in ['desktop/prepare_suite/__init__.py']:
    assert v in (ROOT/name).read_text(),name
assert p['license']=='Apache-2.0'
assert 'Apache License' in (ROOT/'LICENSE').read_text()
print('PASS current product identity, version and license; historical artifacts excluded')
