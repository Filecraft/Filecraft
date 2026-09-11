"""Build a self-contained desktop bundle and ZIP; no runtime dependency install."""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.8.0-beta.1'

def notices(folder):
    folder.mkdir(parents=True,exist_ok=True)
    inventory=[]
    for name in ['Pillow','pypdfium2','pypdf','cryptography','reportlab','defusedxml','cffi','pycparser','charset-normalizer']:
        dist=md.distribution(name);inventory.append({'name':name,'version':dist.version,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License','see bundled notices')})
        for f in dist.files or []:
            if any(word in str(f).lower() for word in ('license','copyright','notice','copying')) and Path(dist.locate_file(f)).is_file():
                target=folder/name/str(f);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dist.locate_file(f),target)
    # Python and bundled Tcl/Tk licenses are required alongside codec notices.
    for base in [Path(sys.base_prefix),Path(sys.base_prefix)/'lib']:
        for pattern in ['LICENSE*','lib/python*/LICENSE*','tcl*/license*','tk*/license*']:
            for p in base.glob(pattern):
                if p.is_file():shutil.copyfile(p,folder/('runtime-'+p.parent.name+'-'+p.name))
    import tkinter
    tcl=Path(tkinter.Tcl().eval('info library'))
    # Homebrew, python.org and Linux distro layouts keep these in different places.
    found=[]
    roots=[tcl,tcl.parent,tcl.parent.parent,Path(sys.base_prefix)/'tcl',Path('/usr/share/doc/tcl8.6'),Path('/usr/share/doc/tk8.6')]
    for base in roots:
        for pattern in ['license.terms','copyright','*/license.terms','*/demos/license.terms']:
            for license_path in base.glob(pattern):
                if license_path.is_file():
                    dest=folder/('tcltk-'+str(len(found))+'-'+license_path.name)
                    shutil.copyfile(license_path,dest);found.append(str(license_path))
    if not found:raise RuntimeError('Tcl/Tk redistribution license not found; do not publish this bundle.')
    (folder/'DEPENDENCIES.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    shutil.copyfile(ROOT/'LICENSE',folder/'PREPARE-LICENSE')

def build():
    system=platform.system();arch=platform.machine().lower()
    work=ROOT/'build'/'desktop-package';out=work/'dist'
    docs=work/'notices';notices(docs)
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','Prepare-Desktop','--distpath',str(out),'--workpath',str(work/'objects'),'--specpath',str(work),'--paths',str(ROOT/'desktop'),'--collect-all','pypdfium2','--collect-all','pypdfium2_raw','--collect-data','reportlab','--collect-all','PIL','--add-data',str(docs)+os.pathsep+'third-party']
    # Keep console bootloader: stdin/out are required for the isolated worker.
    # Native GUI suppresses child consoles on Windows via CREATE_NO_WINDOW.
    args.append(str(ROOT/'desktop'/'launch.py'))
    subprocess.run(args,check=True,cwd=ROOT)
    bundle=out/'Prepare-Desktop';executable=bundle/('Prepare-Desktop.exe' if system=='Windows' else 'Prepare-Desktop')
    subprocess.run([str(executable),'--version'],check=True)
    shutil.copyfile(ROOT/'desktop'/'README.md',bundle/'README.txt')
    shutil.copytree(docs,bundle/'licenses',dirs_exist_ok=True)
    archive=ROOT/'build'/f'Prepare-{VERSION}-desktop-{system.lower()}-{arch}.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(bundle.rglob('*')):
            if p.is_symlink():
                info=zipfile.ZipInfo(str(p.relative_to(out)).replace(os.sep,'/'))
                info.create_system=3;info.external_attr=0o120777<<16
                z.writestr(info,os.readlink(p).encode('utf-8'))
            elif p.is_file():z.write(p,p.relative_to(out))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest,'executable':str(executable)}))

if __name__=='__main__':build()
