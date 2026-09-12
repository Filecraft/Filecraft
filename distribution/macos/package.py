"""Wrap a verified onedir runtime in a real app and read-only Finder DMG.

Build-time dependency: dmgbuild (pinned in distribution/requirements-macos.txt).
No install scripts, daemon, updater, file associations or dependency downloads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]

def run(args,**kw):
    return subprocess.run([str(a) for a in args],check=True,**kw)

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def bundle_info(version,arch):
    if arch not in ('arm64','x86_64'):raise ValueError('Unsupported architecture')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-beta\.\d+)?',version):raise ValueError('Invalid version')
    return dict(CFBundleIdentifier='io.github.filecraft.desktop',CFBundleExecutable='Filecraft-Desktop',
        CFBundleName='Filecraft',CFBundleDisplayName='Filecraft',CFBundlePackageType='APPL',
        CFBundleShortVersionString=version.split('-')[0],CFBundleVersion=version.split('-')[0]+('b'+version.split('-beta.')[1] if '-beta.' in version else ''),
        FilecraftVersion=version,FilecraftArchitecture=arch,CFBundleIconFile='Filecraft.icns',
        LSMinimumSystemVersion='14.0',NSHighResolutionCapable=True,
        NSHumanReadableCopyright='Copyright 2026 Filecraft contributors')

def validate_tree(root):
    root=Path(root).resolve()
    for p in root.rglob('*'):
        if p.is_symlink() and (os.path.isabs(os.readlink(p)) or not p.exists() or not p.resolve().is_relative_to(root)):raise ValueError('Unsafe runtime symlink: '+str(p))
        if not p.is_symlink() and not (p.is_file() or p.is_dir()):raise ValueError('Special runtime file: '+str(p))

def signature_status(text):
    if 'Signature=adhoc' in text:return 'ad-hoc'
    if 'not signed at all' in text:return 'unsigned'
    if 'Authority=Developer ID Application:' in text and re.search(r'TeamIdentifier=[A-Z0-9]{10}',text):return 'developer-id'
    raise ValueError('Unknown signing state')

def build(bundle,output,version):
    bundle=bundle.resolve();output=output.resolve();validate_tree(bundle)
    exe=bundle/'Filecraft-Desktop'
    actual=subprocess.check_output([str(exe),'--version'],text=True).strip()
    if actual!=version:raise ValueError('Runtime version mismatch')
    arch=subprocess.check_output(['lipo','-archs',str(exe)],text=True).strip()
    info=bundle_info(version,arch)
    output.mkdir(parents=True,exist_ok=True)
    filename=f'Filecraft-{version}-macos-{arch}.dmg';final=output/filename
    if final.exists():raise FileExistsError(final)
    identity=os.environ.get('FILECRAFT_SIGN_IDENTITY')
    profile=os.environ.get('FILECRAFT_NOTARY_PROFILE')
    if profile and not identity:raise ValueError('Notarization requires Developer ID signing')
    with tempfile.TemporaryDirectory(prefix='filecraft-dmg-',dir=output) as td:
        work=Path(td);app=work/'Filecraft.app';contents=app/'Contents';contents.mkdir(parents=True)
        macos=contents/'MacOS';macos.mkdir()
        resources=contents/'Resources';resources.mkdir()
        shutil.copytree(bundle,resources/'runtime',symlinks=True)
        # Keep the real executable in MacOS so Cocoa identifies the app.
        # Runtime data lives in Resources, reached by PyInstaller's normal path.
        shutil.copy2(resources/'runtime'/'Filecraft-Desktop',macos/'Filecraft-Desktop')
        (resources/'runtime'/'Filecraft-Desktop').unlink()
        (contents/'Frameworks').symlink_to('Resources/runtime/_internal')
        (contents/'Info.plist').write_bytes(plistlib.dumps(info,sort_keys=True))
        from PIL import Image,ImageDraw
        icon=Image.open(ROOT/'docs/assets/filecraft-avatar.png').convert('RGBA')
        icon.save(resources/'Filecraft.icns',format='ICNS')
        # The established brand, not a new visual identity.
        bg=Image.new('RGB',(660,420),'#faf9f6');draw=ImageDraw.Draw(bg)
        draw.text((36,28),'FILECRAFT',fill='#222824',font_size=24)
        draw.text((36,65),'Drag Filecraft to Applications',fill='#61655f',font_size=20)
        draw.line((290,220,365,220),fill='#b54120',width=4)
        draw.polygon([(365,212),(378,220),(365,228)],fill='#b54120')
        draw.text((36,352),'Then eject this disk and open Filecraft from Applications.',fill='#61655f',font_size=16)
        bg.save(work/'background.png')
        (work/'Read me first.txt').write_text('Filecraft '+version+'\n\nDrag Filecraft.app to Applications. Eject this disk, then open Filecraft.\nQuit the old version before replacing it. Keep a copy if rollback is needed.\nNo automatic updater or background service is installed.\nUninstall: quit Filecraft and move the app to Trash. Your files are not removed.\n\n'+('Developer ID signing requested; consult release manifest for verified notarization.\n' if identity else 'NOT DEVELOPER ID SIGNED. NOT NOTARIZED. macOS may block launch.\n')+'Do not disable system security. A matching checksum proves byte identity, not safety.\nOfficial downloads: https://filecraft.github.io/download/\n',encoding='utf-8')
        validate_tree(app)
        if identity:
            if not identity.startswith('Developer ID Application:'):raise ValueError('Require Developer ID Application identity')
            # Sign Mach-O leaves before frameworks and app; do not use --deep signing.
            magic={b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'}
            for p in sorted(app.rglob('*'),key=lambda x:len(x.parts),reverse=True):
                if p.is_file() and not p.is_symlink():
                    with p.open('rb') as f:is_macho=f.read(4) in magic
                    if is_macho:run(['codesign','--force','--sign',identity,'--options','runtime','--timestamp',p])
            for p in sorted(app.rglob('*.framework'),key=lambda x:len(x.parts),reverse=True):
                if not p.is_symlink():run(['codesign','--force','--sign',identity,'--options','runtime','--timestamp',p])
        run(['codesign','--force','--sign',identity or '-',*(['--options','runtime','--timestamp'] if identity else []),app])
        run(['codesign','--verify','--deep','--strict',app])
        signature=subprocess.run(['codesign','-dv','--verbose=4',str(app)],capture_output=True,text=True)
        status=signature_status(signature.stderr)
        notarization='not-notarized'
        if profile:
            upload=work/'notary.zip';run(['ditto','-c','-k','--keepParent',app,upload])
            response=subprocess.check_output(['xcrun','notarytool','submit',str(upload),'--keychain-profile',profile,'--wait','--output-format','json'])
            if json.loads(response)['status']!='Accepted':raise RuntimeError('Notarization not accepted')
            run(['xcrun','stapler','staple',app]);run(['xcrun','stapler','validate',app]);notarization='notarized-stapled'
        import dmgbuild
        dmgbuild.build_dmg(str(final),'Filecraft',settings=dict(files=[str(app),str(work/'Read me first.txt')],
            symlinks={'Applications':'/Applications'},background=str(work/'background.png'),
            icon_locations={'Filecraft.app':(180,220),'Applications':(480,220),'Read me first.txt':(580,340)},
            window_rect=((120,120),(660,420)),icon_size=88,text_size=14,format='UDZO',
            show_status_bar=False,show_tab_view=False,show_toolbar=False,show_pathbar=False,
            arrange_by=None,default_view='icon-view',include_icon_view_settings=True))
        if identity:run(['codesign','--sign',identity,'--timestamp',final])
        if profile:
            response=subprocess.check_output(['xcrun','notarytool','submit',str(final),'--keychain-profile',profile,'--wait','--output-format','json'])
            if json.loads(response)['status']!='Accepted':raise RuntimeError('DMG notarization not accepted')
            run(['xcrun','stapler','staple',final]);run(['xcrun','stapler','validate',final])
        run(['hdiutil','verify',final])
        sha=digest(final);final.with_suffix('.dmg.sha256').write_text(sha+'  '+filename+'\n')
        record=dict(product='Filecraft',version=version,channel='beta',platform='macos',architecture=arch,
            artifact_type='dmg',filename=filename,bytes=final.stat().st_size,sha256=sha,
            signing=status,notarization=notarization,classification='consumer',bundle_id=info['CFBundleIdentifier'],
            minimum_os='macOS 14; qualification evidence lists tested hosts',
            installation=['Open the DMG','Drag Filecraft to Applications','Eject the disk','Open Filecraft from Applications'],
            reproducibility='Pinned runtime input and packaging recipe; DMG filesystem timestamps are not bit-reproducible')
        (output/(filename+'.metadata.json')).write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record))
    return final

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default=json.loads((ROOT/'product.json').read_text())['version']);a=p.parse_args()
    build(a.bundle,a.output,a.version)
