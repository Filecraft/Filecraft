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
VERSION=json.loads((ROOT/'product.json').read_text())['version']


def openssl_versions():
    """Both Python TLS and cryptography may carry distinct OpenSSL builds."""
    import ssl
    from cryptography.hazmat.backends.openssl.backend import backend
    return {'python': ssl.OPENSSL_VERSION, 'cryptography': backend.openssl_version_text()}


def openssl_notices(folder):
    """Build-time upstream retrieval; fail closed on unknown/missing notices."""
    import re
    import urllib.request
    versions = openssl_versions()
    records = []
    for description in sorted(set(versions.values())):
        match = re.match(r'^OpenSSL ((?:3|4)\.\d+\.\d+)\b', description)
        if not match:
            raise RuntimeError('Review unsupported TLS license before packaging: '+description)
        version = match.group(1)
        target = folder/('openssl-'+version)
        target.mkdir(parents=True, exist_ok=True)
        files = []
        for name in ('LICENSE.txt', 'AUTHORS.md', 'include/openssl/opensslv.h.in'):
            url = f'https://raw.githubusercontent.com/openssl/openssl/openssl-{version}/{name}'
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            if name.endswith('.h.in'):
                # Retain the exact upstream copyright/license comment, not a paraphrase.
                start = data.index(b'/*'); end = data.index(b'*/', start)+2
                data = data[start:end]+b'\n'
                output = 'COPYRIGHT.txt'
            else:
                output = name
            if not data or (output == 'LICENSE.txt' and b'Apache License' not in data):
                raise RuntimeError('Unexpected OpenSSL legal text: '+url)
            (target/output).write_bytes(data)
            files.append({'file': output, 'source': url, 'sha256': hashlib.sha256(data).hexdigest()})
        records.append({'version': version, 'files': files})
    (folder/'OPENSSL-PROVENANCE.json').write_text(json.dumps({'runtimes': versions, 'sources': records}, indent=2)+'\n', encoding='utf-8')


def prune_unused_fonts(bundle):
    """Exclude separable, unused GPL-exception fonts; leave Vera and its license."""
    for path in bundle.rglob('*'):
        if path.is_file() and path.name.lower().startswith('darkgarden'):
            path.unlink()
    if any(p.name.lower().startswith('darkgarden') for p in bundle.rglob('*')):
        raise RuntimeError('Unused DarkGarden assets remain in package')
    fonts = list(bundle.rglob('Vera.ttf'))
    if not fonts or not all((font.parent/'bitstream-vera-license.txt').is_file() for font in fonts):
        raise RuntimeError('Vera output font and its license are required')

def notices(folder):
    if folder.exists():shutil.rmtree(folder)
    folder.mkdir(parents=True,exist_ok=True)
    inventory=[]
    for name in ['Pillow','pypdfium2','pypdf','cryptography','reportlab','defusedxml','cffi','pycparser','charset-normalizer']:
        dist=md.distribution(name);inventory.append({'name':name,'version':dist.version,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License','see bundled notices')})
        for f in dist.files or []:
            if any(word in str(f).lower() for word in ('license','copyright','notice','copying')) and Path(dist.locate_file(f)).is_file():
                target=folder/name/str(f);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dist.locate_file(f),target)
        if name=='pypdfium2':
            # Generic BSD templates are not author attribution. Keep exact SPDX headers.
            headers=set()
            for f in dist.files or []:
                if str(f).endswith('.py'):
                    data=Path(dist.locate_file(f)).read_bytes()
                    headers.update(line for line in data.splitlines() if line.startswith(b'# SPDX-'))
            if not any(b'SPDX-FileCopyrightText:' in line for line in headers):
                raise RuntimeError('pypdfium2 source copyright attribution missing')
            target=folder/name/'SOURCE-ATTRIBUTION.txt';target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(b'\n'.join(sorted(headers))+b'\n')
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
    openssl_notices(folder)
    (folder/'DEPENDENCIES.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    shutil.copyfile(ROOT/'LICENSE',folder/'FILECRAFT-LICENSE')
    shutil.copyfile(ROOT/'NOTICE',folder/'FILECRAFT-NOTICE')
    shutil.copyfile(ROOT/'docs/LICENSING.md',folder/'FILECRAFT-LICENSING.md')
    shutil.copyfile(ROOT/'docs/DEPENDENCIES.md',folder/'FILECRAFT-DEPENDENCIES.md')
    shutil.copyfile(ROOT/'docs/ACKNOWLEDGMENTS.md',folder/'FILECRAFT-ACKNOWLEDGMENTS.md')

def build():
    system=platform.system();arch=platform.machine().lower()
    work=ROOT/'build'/'desktop-package';out=work/'dist'
    docs=work/'notices';notices(docs)
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','Filecraft-Desktop','--distpath',str(out),'--workpath',str(work/'objects'),'--specpath',str(work),'--paths',str(ROOT/'desktop'),'--collect-all','pypdfium2','--collect-all','pypdfium2_raw','--collect-data','reportlab','--collect-all','PIL','--add-data',str(docs)+os.pathsep+'third-party']
    # Keep console bootloader: stdin/out are required for the isolated worker.
    # Native GUI suppresses child consoles on Windows via CREATE_NO_WINDOW.
    args.append(str(ROOT/'desktop'/'launch.py'))
    subprocess.run(args,check=True,cwd=ROOT)
    bundle=out/'Filecraft-Desktop';executable=bundle/('Filecraft-Desktop.exe' if system=='Windows' else 'Filecraft-Desktop')
    subprocess.run([str(executable),'--version'],check=True)
    shutil.copyfile(ROOT/'desktop'/'README.md',bundle/'README.txt')
    shutil.copytree(docs,bundle/'licenses',dirs_exist_ok=True)
    prune_unused_fonts(bundle)
    archive=ROOT/'build'/f'Filecraft-{VERSION}-desktop-{system.lower()}-{arch}.zip'
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
