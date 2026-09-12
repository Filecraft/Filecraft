"""Deterministic MV3 adapters over the actual local Workbench; no remote code."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_workbench import HANDLER
VERSION=json.loads((ROOT/'product.json').read_text())['version']
def build():
    results=[]
    for browser in ('chromium','firefox'):
        folder=ROOT/'build/extension'/browser
        if folder.is_symlink():raise ValueError('Refusing a symlink extension staging directory')
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir(parents=True,exist_ok=False)
        manifest={'manifest_version':3,'name':'Filecraft: local document workspace','version':VERSION.split('-')[0],'description':'Prepare a PDF copy for your requirements. Reorder pages, verify output bytes and save a receipt. No uploads.','action':{'default_title':'Open Filecraft workspace','default_icon':{'16':'icons/16.png','32':'icons/32.png'}},'icons':{str(n):f'icons/{n}.png' for n in (16,32,48,128)},'permissions':[],'host_permissions':[],'content_security_policy':{'extension_pages':"default-src 'none'; script-src 'self'; style-src 'self'; worker-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"}}
        if browser=='chromium':manifest['background']={'service_worker':'background.js'}
        else:
            manifest['background']={'scripts':['background.js']}
            manifest['browser_specific_settings']={'gecko':{'id':'workspace@filecraft.github.io','strict_min_version':'142.0','data_collection_permissions':{'required':['none']}}}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        (folder/'background.js').write_text("'use strict';\nconst api=globalThis.browser||globalThis.chrome;\napi.action.onClicked.addListener(()=>api.tabs.create({url:api.runtime.getURL('workspace/index.html')}));\n",encoding='utf-8')
        workspace=folder/'workspace';workspace.mkdir(exist_ok=True)
        for name in ('style.css','app.js','document-engine.js','readiness-ui.js'):
            shutil.copyfile(ROOT/'workbench'/name,workspace/name)
        html=(ROOT/'workbench/index.html').read_text(encoding='utf-8').replace('src="worker-bundle.js"','src="worker-config.js"').replace('worker-src blob:','worker-src \'self\'')
        (workspace/'index.html').write_text(html,encoding='utf-8')
        (workspace/'worker-config.js').write_text("const PREPARE_STATIC_WORKER='worker.js';\n",encoding='utf-8')
        worker=(ROOT/'pdf/vendor/pdf-lib.min.js').read_text(encoding='utf-8')+'\n'+(ROOT/'pdf/document.js').read_text(encoding='utf-8')+'\n'+HANDLER
        (workspace/'worker.js').write_text(worker,encoding='utf-8')
        for name in ('LICENSE','NOTICE'):shutil.copyfile(ROOT/name,folder/name)
        shutil.copyfile(ROOT/'pdf/THIRD-PARTY.md',folder/'THIRD-PARTY.txt')
        shutil.copyfile(ROOT/'extension/README.md',folder/'README.txt')
        shutil.copytree(ROOT/'extension/icons',folder/'icons',dirs_exist_ok=True)
        (folder/'vendor').mkdir(exist_ok=True)
        for p in (ROOT/'pdf/vendor').iterdir():
            if p.name.startswith('LICENSE') or p.name in ('PROVENANCE.json','README.md'):shutil.copyfile(p,folder/'vendor'/p.name)
        archive=ROOT/'build'/f'Filecraft-{VERSION}-extension-{browser}.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    info=zipfile.ZipInfo(p.relative_to(folder).as_posix(),date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
        digest=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
        results.append({'browser':browser,'path':str(archive),'bytes':archive.stat().st_size,'sha256':digest})
    print(json.dumps(results,indent=2))
if __name__=='__main__':build()
