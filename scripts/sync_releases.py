"""Fetch actual public releases; never synthesize prospective asset URLs."""
import argparse,json,subprocess,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('site',type=Path);p.add_argument('--current',required=True);args=p.parse_args()
pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp','repos/Filecraft/Filecraft/releases?per_page=100'],text=True))
releases=sorted([r for page in pages for r in page],key=lambda r:r['published_at'] or '',reverse=True)
releases=[r for r in releases if not r['draft']]
current=next(r for r in releases if r['tag_name']==args.current)
args.site.joinpath('releases.json').write_text(json.dumps([{'tag':r['tag_name'],'url':r['html_url'],'name':r['name'],'published':r['published_at'],'prerelease':r['prerelease'],'current':r['tag_name']==args.current,'assets':[{'name':a['name'],'url':a['browser_download_url'],'bytes':a['size']} for a in r['assets']]} for r in releases],indent=2)+'\n')
assets=[]
for a in current['assets']:
    name=a['name']
    if not name.endswith('.zip'):continue
    checksum=next(x for x in current['assets'] if x['name']==name+'.sha256')
    import urllib.request
    with urllib.request.urlopen(checksum['browser_download_url'],timeout=60) as response:digest=response.read().decode().split()[0]
    if not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError('Malformed public checksum')
    platform='windows' if 'windows' in name else 'linux' if 'linux' in name else 'macos' if 'darwin' in name else 'browser'
    arch='Apple Silicon' if 'arm64' in name else 'Intel x64' if 'x86_64' in name else 'x64' if 'amd64' in name else 'Chromium / Edge' if 'chromium' in name else 'Firefox temporary install' if 'firefox' in name else 'Web / offline ZIP'
    assets.append({'name':name,'label':name.removesuffix('.zip'),'url':a['browser_download_url'],'bytes':a['size'],'sha256':digest,'platform':platform,'architecture':arch,'version':args.current.removeprefix('v'),'notes':'Self-contained desktop; optional OCR/media engines separate.' if platform!='browser' else 'Local PDF workspace; extension stores not published.', 'channel':'beta' if current['prerelease'] else 'stable','license':'Apache-2.0' if tuple(map(int,args.current.lstrip('v').split('-')[0].split('.'))) >= (0,9,0) else 'historical terms'})
args.site.joinpath('downloads.json').write_text(json.dumps(assets,indent=2)+'\n')
print('Actual releases',len(releases),'current ZIPs',len(assets))
