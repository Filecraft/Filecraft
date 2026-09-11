"""Allowlisted, reproducible offline companion archive; stdlib only."""
from pathlib import Path
import hashlib
import json
import zipfile

VERSION='0.5.0'
FILES=['index.html','style.css','core.js','app.js','README.txt']
def validate_portable(expanded,archive):
    if not 0<expanded<200_000 or not 0<archive<100_000:
        raise ValueError('Portable must be below 200 KB expanded and 100 KB ZIP')

def main():
    root=Path(__file__).resolve().parents[1]
    output=root/'build'/f'Prepare-{VERSION}-portable.zip'
    output.parent.mkdir(exist_ok=True)
    payload={name:(root/'portable'/name).read_bytes() for name in FILES}
    payload.update({name:(root/name).read_bytes() for name in ['LICENSE','NOTICE']})
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(f'Prepare-Portable/{name}',date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    expanded=sum(map(len,payload.values()))
    validate_portable(expanded,output.stat().st_size)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(payload)
    output.with_suffix('.zip.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
    sizes={'version':VERSION,'expanded':expanded,'archive':output.stat().st_size,'files':len(payload)}
    (root/'build'/'portable-size.json').write_text(json.dumps(sizes,indent=2)+'\n')
    print('PASS portable package',sizes)

if __name__=='__main__':main()
