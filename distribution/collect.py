"""Collect final installers from download-artifact output; reject collisions."""
import argparse
from pathlib import Path
import shutil
import os
import stat

def collect(source,destination):
    source=Path(source).resolve();destination=Path(destination).resolve()
    candidates=[];seen=set()
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.is_symlink() or destination in p.parents:continue
        relative=p.relative_to(source)
        if not relative.parts[0].startswith('consumer-'):continue
        if p.suffix not in ('.dmg','.deb','.exe') and not p.name.endswith(('.metadata.json','.sha256')):continue
        if p.name in seen:raise ValueError('Duplicate artifact filename: '+p.name)
        seen.add(p.name);candidates.append(p)
    if not candidates:raise ValueError('No consumer artifacts')
    destination.mkdir(parents=True,exist_ok=False)
    for p in candidates:
        # Disallow final-component link swaps between discovery and open.
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('Not a regular artifact')
            with (destination/p.name).open('xb') as output:shutil.copyfileobj(stream,output)
    return len(candidates)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path);args=parser.parse_args()
    print('Collected',collect(args.source,args.destination),'final installer files/sidecars')
