"""Copy canonical product/selected docs and actual workspace to the companion site."""
from pathlib import Path
import json
import shutil
import sys
import subprocess
ROOT=Path(__file__).resolve().parents[1]
site=Path(sys.argv[1]).resolve()
if not (site/'.git').exists():raise SystemExit('Expected existing site checkout.')
remote=subprocess.check_output(['git','-C',str(site),'remote','get-url','origin'],text=True).strip().removesuffix('.git')
if remote.lower() not in ('git@github.com:filecraft/filecraft.github.io','https://github.com/filecraft/filecraft.github.io'):
    raise SystemExit('Refusing sync: only Filecraft/filecraft.github.io is authorized.')
shutil.copyfile(ROOT/'product.json',site/'product.json')
for source,target in [('desktop/README.md','DESKTOP-SUITE.md'),('docs/DEPENDENCIES.md','DEPENDENCIES.md'),('docs/LICENSING.md','LICENSING.md'),('docs/PRODUCT-DECISION-09.md','PRODUCT-DECISION-09.md'),('docs/AUTO-FIT.md','AUTO-FIT.md'),('docs/ONLINE-ASSISTANCE.md','ONLINE-ASSISTANCE.md'),('docs/DOCUMENTATION-HOSTING.md','DOCUMENTATION-HOSTING.md'),('docs/AI-DISCLOSURE.md','AI-DISCLOSURE.md'),('docs/MIGRATION.md','MIGRATION.md')]:
    shutil.copyfile(ROOT/source,site/target)
shutil.copytree(ROOT/'workbench',site/'workspace',dirs_exist_ok=True)
for name in ['LICENSE','NOTICE']:shutil.copyfile(ROOT/name,site/'workspace'/name)
shutil.copyfile(ROOT/'pdf/THIRD-PARTY.md',site/'workspace/THIRD-PARTY.txt')
shutil.copytree(ROOT/'pdf/vendor',site/'workspace/vendor',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.js'))
p=site/'workspace/index.html';html=p.read_text()
description='Prepare PDF copies locally, check personal requirements and verify saved bytes with an unsigned receipt.'
url='https://filecraft.github.io/workspace/'
meta=f'<link rel="canonical" href="{url}"><meta name="description" content="{description}"><meta property="og:type" content="website"><meta property="og:title" content="Filecraft local workspace"><meta property="og:description" content="{description}"><meta property="og:url" content="{url}"><meta property="og:image" content="https://filecraft.github.io/assets/social-preview.png"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Filecraft local workspace"><meta name="twitter:description" content="{description}"><meta name="twitter:image" content="https://filecraft.github.io/assets/social-preview.png">'
html=html.replace('<head>','<head>'+meta).replace('No account, uploads, analytics, fonts, storage or automatic updates.','No account, document uploads, analytics, remote fonts or persistent workspace storage. This hosted page downloads static assets from GitHub Pages; normal hosting metadata is separate from document processing. Use the offline ZIP to avoid contacting the site.')
p.write_text(html)
print('Synced product metadata, current docs and functional local workspace to',site)
