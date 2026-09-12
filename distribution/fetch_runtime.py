"""Download only hash-locked public runtime bytes; never execute partial input."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def verify(path,item):
    if path.stat().st_size!=item['bytes']:raise ValueError('Runtime size mismatch')
    with path.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=item['sha256']:raise ValueError('Runtime checksum mismatch')

def fetch(platform,output):
    locks=json.loads((ROOT/'distribution/runtime-lock.json').read_text())
    item=next(a for a in locks['assets'] if a['filename'].endswith('-desktop-'+platform+'.zip'))
    output.mkdir(parents=True,exist_ok=True);archive=output/item['filename']
    if not archive.exists():
        partial=archive.with_suffix('.part')
        try:
            with urllib.request.urlopen(item['url'],timeout=90) as r,partial.open('wb') as f:shutil.copyfileobj(r,f)
            verify(partial,item);partial.replace(archive)
        finally:partial.unlink(missing_ok=True)
    verify(archive,item)
    target=output/'runtime'
    if target.exists():raise FileExistsError(target)
    with zipfile.ZipFile(archive) as z:
        for i in z.infolist():
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename:raise ValueError('Unsafe archive path')
            if stat.S_ISLNK(i.external_attr>>16):
                link=PurePosixPath(z.read(i).decode())
                resolved=(target/i.filename).parent.joinpath(str(link)).resolve()
                if link.is_absolute() or not resolved.is_relative_to(target.resolve()):raise ValueError('Escaping archive symlink')
        if sys.platform=='darwin':subprocess.run(['ditto','-x','-k',str(archive),str(target)],check=True)
        else:
            z.extractall(target)
            for i in z.infolist():
                p=target/i.filename;mode=i.external_attr>>16
                if stat.S_ISLNK(mode):p.unlink();p.symlink_to(z.read(i).decode())
                elif mode and not p.is_dir():os.chmod(p,mode&0o777)
    print(target/'Filecraft-Desktop');return target/'Filecraft-Desktop'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('platform',choices=['darwin-arm64','darwin-x86_64','windows-amd64','linux-x86_64']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();fetch(a.platform,a.output)
