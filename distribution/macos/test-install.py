"""Mount and qualify a DMG; never overwrite a user's installed application."""
import argparse
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]

def run(args,**kw):return subprocess.run([str(x) for x in args],check=True,**kw)
def main():
    p=argparse.ArgumentParser();p.add_argument('dmg',type=Path);a=p.parse_args()
    info=plistlib.loads(subprocess.check_output(['hdiutil','attach','-readonly','-nobrowse','-plist',str(a.dmg)]))
    mount=next(Path(e['mount-point']) for e in info['system-entities'] if 'mount-point' in e)
    try:
        assert (mount/'Applications').is_symlink() and (mount/'Applications').readlink()==Path('/Applications')
        assert (mount/'.DS_Store').is_file()
        with tempfile.TemporaryDirectory(prefix='filecraft-install-') as td:
            app=Path(td)/'Applications/Filecraft.app';app.parent.mkdir()
            run(['ditto',mount/'Filecraft.app',app])
            run(['codesign','--verify','--deep','--strict',app])
            bundle=plistlib.loads((app/'Contents/Info.plist').read_bytes())
            assert bundle['CFBundleIdentifier']=='io.github.filecraft.desktop'
            exe=app/'Contents/MacOS/Filecraft-Desktop'
            run([sys.executable,ROOT/'desktop/check_frozen.py',exe])
            assessment=subprocess.run(['spctl','--assess','--type','execute',str(app)],capture_output=True,text=True)
            staple=subprocess.run(['xcrun','stapler','validate',str(app)],capture_output=True,text=True)
            record=json.loads(a.dmg.with_name(a.dmg.name+'.metadata.json').read_text())
            if record['notarization']=='notarized-stapled':
                assert assessment.returncode==0 and staple.returncode==0
            record=dict(installed_runtime_passed=True,bundle_id=bundle['CFBundleIdentifier'],architecture=bundle['FilecraftArchitecture'],gatekeeper_accepted=assessment.returncode==0,staple_valid=staple.returncode==0,gui_export_tested=False)
            a.dmg.with_name(a.dmg.name+'.qualification.json').write_text(json.dumps(record,indent=2)+'\n')
            print(json.dumps(record))
    finally:run(['hdiutil','detach',mount])
if __name__=='__main__':main()
