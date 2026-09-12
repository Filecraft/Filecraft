"""Canonical final-artifact manifest. Never trusts a build's success alone.

Create after native qualification; verify --public after draft publication,
before any consumer website points at the new release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
REPO='https://github.com/Filecraft/Filecraft'
MATRIX={('macos','arm64','dmg'),('macos','x86_64','dmg'),('windows','x64','exe'),('ubuntu-24.04','amd64','deb')}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def validate_artifact(root,a,version):
    try:
        name=a['filename'];key=(a['platform'],a['architecture'],a['artifact_type'])
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.~+-]+',name):raise ValueError('Unsafe filename')
        if a['version']!=version or a['product']!='Filecraft' or a['channel']!='beta':raise ValueError('Stale product/version')
        if key not in MATRIX:raise ValueError('Unknown platform/architecture/type')
        extension={'dmg':'.dmg','exe':'.exe','deb':'.deb'}[key[2]]
        if not name.endswith(extension):raise ValueError('Wrong artifact extension')
        if a['signing'] not in ('unsigned','ad-hoc','developer-id','authenticode'):raise ValueError('Unknown signing state')
        if a['notarization'] not in ('not-notarized','notarized-stapled','not-applicable'):raise ValueError('Unknown notarization state')
        if a['notarization']=='notarized-stapled' and a['signing']!='developer-id':raise ValueError('Untrusted notarization claim')
        if not a['installation'] or a['classification']!='consumer':raise ValueError('Missing installation contract')
        file=root/name
        if not file.is_file() or file.is_symlink():raise ValueError('Missing artifact')
        if file.stat().st_size!=a['bytes']:raise ValueError('Wrong file size')
        if not re.fullmatch('[a-f0-9]{64}',a['sha256']) or digest(file)!=a['sha256']:raise ValueError('Checksum mismatch')
        sidecar=root/(name+'.sha256')
        if not sidecar.is_file() or sidecar.read_text().strip()!=a['sha256']+'  '+name:raise ValueError('Missing/mismatched checksum sidecar')
    except (KeyError,TypeError,OSError) as e:raise ValueError('Invalid artifact metadata') from e

def validate_matrix(artifacts):
    keys=[(a['platform'],a['architecture'],a['artifact_type']) for a in artifacts]
    if len(keys)!=len(MATRIX) or set(keys)!=MATRIX:raise ValueError('Incomplete or duplicate consumer artifact matrix')

def normalize(a):
    if 'filename' in a:return a
    windows=a['platform']=='windows'
    return dict(product='Filecraft',version=a['version'],channel='beta',platform=a['platform'],architecture=a['architecture'],artifact_type='exe' if windows else 'deb',filename=a['artifact'],bytes=a['bytes'],sha256=a['sha256'],signing='authenticode' if a['signed'] else 'unsigned',notarization='not-applicable',classification='consumer',installation=(['Run the installer','Install for your Windows account','Open Filecraft from Start'] if windows else ['On Ubuntu 24.04 x64, open a terminal in Downloads','Run: sudo apt install ./'+a['artifact'],'Open Filecraft from Applications']),minimum_os='Windows 10/11 x64' if windows else 'Ubuntu 24.04 x64 with X11/XWayland')

def create(root,version,source,run_url):
    if not re.fullmatch('[a-f0-9]{40}',source):raise ValueError('Source must be an exact commit')
    artifacts=[]
    for p in sorted(root.glob('*.json')):
        if p.name=='release-manifest.json':continue
        data=json.loads(p.read_text())
        if 'sha256' not in data:continue
        a=normalize(data);validate_artifact(root,a,version)
        a.update(download_url=REPO+'/releases/download/v'+version+'/'+urllib.parse.quote(a['filename']),github_release=REPO+'/releases/tag/v'+version,build_run=run_url)
        artifacts.append(a)
    validate_matrix(artifacts)
    manifest=dict(schema=1,product='Filecraft',version=version,channel='beta',tag='v'+version,source_commit=source,release_date=None,github_release=REPO+'/releases/tag/v'+version,artifacts=artifacts)
    (root/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def resolve_tag(tag):
    if not re.fullmatch(r'v\d+\.\d+\.\d+-beta\.\d+',tag):raise ValueError('Invalid release tag')
    def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Filecraft/Filecraft/'+path]))
    obj=api('git/ref/tags/'+tag)['object'];seen=set()
    for _ in range(10):
        sha=obj['sha']
        if not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('Invalid tag object')
        if obj['type']=='commit':return sha
        if obj['type']!='tag' or sha in seen:raise ValueError('Invalid tag chain')
        seen.add(sha);obj=api('git/tags/'+sha)['object']
    raise ValueError('Tag chain too deep')

def verify_source(manifest):
    if manifest['tag']!='v'+manifest['version']:raise ValueError('Stale tag version')
    if not re.fullmatch('[a-f0-9]{40}',manifest['source_commit']):raise ValueError('Invalid source commit')
    if resolve_tag(manifest['tag'])!=manifest['source_commit']:raise ValueError('Release tag source mismatch')

def verify_public(root,manifest):
    validate_matrix(manifest['artifacts'])
    verify_source(manifest)
    for artifact in manifest['artifacts']:validate_artifact(root,artifact,manifest['version'])
    release=json.loads(subprocess.check_output(['gh','api','repos/Filecraft/Filecraft/releases/tags/'+manifest['tag']]))
    if release['draft'] or not release['published_at']:raise ValueError('Release is not public')
    assets={a['name']:a for a in release['assets']}
    for a in manifest['artifacts']:
        remote=assets.get(a['filename'])
        if not remote or remote['size']!=a['bytes'] or remote['browser_download_url']!=a['download_url']:raise ValueError('Missing/stale public artifact')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/a['filename'];h=hashlib.sha256();size=0
            with urllib.request.urlopen(a['download_url'],timeout=90) as response,p.open('wb') as out:
                for block in iter(lambda:response.read(1024*1024),b''):out.write(block);h.update(block);size+=len(block)
            if size!=a['bytes'] or h.hexdigest()!=a['sha256']:raise ValueError('Public bytes do not match')
            with urllib.request.urlopen(a['download_url']+'.sha256',timeout=30) as response:
                if response.read().decode().strip()!=a['sha256']+'  '+a['filename']:raise ValueError('Public checksum mismatch')
    manifest['release_date']=release['published_at']
    (root/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('PASS exact public bytes, sizes, URLs and checksum sidecars for all consumer artifacts')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--version');p.add_argument('--source');p.add_argument('--run-url');p.add_argument('--public',action='store_true');a=p.parse_args()
    if a.public:verify_public(a.root,json.loads((a.root/'release-manifest.json').read_text()))
    else:create(a.root,a.version,a.source,a.run_url)
