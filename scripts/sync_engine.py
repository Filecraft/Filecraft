"""Copy the single authoritative shared engine into the offline bundle."""
from pathlib import Path
import sys
r=Path(__file__).resolve().parents[1]
src=(r/'engine/document-engine.js').read_bytes()
out=r/'portable/document-engine.js'
if '--check' in sys.argv:
    assert out.read_bytes()==src,'Run python3 scripts/sync_engine.py'
else:
    out.write_bytes(src)
print('PASS shared engine bundle parity')
