"""Scan tracked and non-ignored source text; never rewrite vendor bytes."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
roots=[ROOT]+[Path(p).resolve() for p in sys.argv[1:]]
findings=[];preserved=[];files=0
for root in roots:
    names=subprocess.check_output(['git','-C',str(root),'ls-files','-z','--cached','--others','--exclude-standard']).decode().split('\0')
    for name in sorted(set(filter(None,names))):
        path=root/name
        if not path.is_file():continue
        data=path.read_bytes()
        if b'\x00' in data:continue
        try:text=data.decode('utf-8')
        except UnicodeDecodeError:continue
        files+=1
        count=text.count(chr(0x2014))
        if count:
            item={'repo':root.name,'file':name,'count':count}
            if name=='pdf/vendor/pdf-lib.min.js':preserved.append(item)
            else:findings.append(item)
print(json.dumps({'text_files_scanned':files,'presentation_em_dashes':findings,'preserved_vendor_character_map':preserved},indent=2))
raise SystemExit(bool(findings))
