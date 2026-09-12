"""Exercise installed GUI through OS input, never through internal conversion calls.
Run on an isolated interactive Windows desktop or Linux Xvfb display.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]

def wait(check,label,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=check()
        if value:return value
        time.sleep(.2)
    raise RuntimeError('Timed out: '+label)

def main():
    p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    import pyautogui as ui
    from PIL import Image
    ui.PAUSE=.3;a.evidence.mkdir(parents=True,exist_ok=True)
    samples=ROOT/'build/samples/installed-gui';samples.mkdir(parents=True,exist_ok=True)
    source=samples/'source.png';destination=samples/('export-'+str(time.time_ns())+'.png')
    Image.new('RGB',(80,60),'#b54120').save(source);before=hashlib.sha256(source.read_bytes()).hexdigest()
    # Derive widget locations from the same version's native layout. This does
    # not test processing: only OS-driven installed UI may create the output.
    sys.path.insert(0,str(ROOT/'desktop'))
    import tkinter as tk
    from prepare_suite.gui import App
    root=tk.Tk();app=App(root);root.update()
    def point(w):return (w.winfo_rootx()-root.winfo_rootx()+w.winfo_width()/2,w.winfo_rooty()-root.winfo_rooty()+w.winfo_height()/2)
    choose=point(app.open_button);app.load_source(str(source));root.update();save=point(app.save_button);root.destroy()
    def locate():
        if sys.platform=='win32':
            import pygetwindow as gw
            windows=[w for w in gw.getWindowsWithTitle('Filecraft | local document suite') if w.visible]
            if windows:
                w=windows[0];w.activate()
                # Tk root coords start at client area, excluding frame/title.
                import ctypes
                pt=(ctypes.c_long*2)(0,0);ctypes.windll.user32.ClientToScreen(w._hWnd,pt)
                return tuple(pt)
        else:
            r=subprocess.run(['xdotool','search','--onlyvisible','--name','^Filecraft \\| local document suite$'],capture_output=True,text=True)
            if r.returncode==0:
                win=r.stdout.splitlines()[0];subprocess.run(['xdotool','windowfocus',win],check=True)
                values=dict(line.split('=',1) for line in subprocess.check_output(['xdotool','getwindowgeometry','--shell',win],text=True).splitlines() if '=' in line)
                return int(values['X']),int(values['Y'])
        return None
    processes=[]
    try:
        for launch in range(2):
            proc=subprocess.Popen([a.executable]);processes.append(proc)
            origin=wait(locate,'installed window');ui.screenshot().save(a.evidence/f'launch-{launch}.png')
            if launch==0:
                ui.click(origin[0]+choose[0],origin[1]+choose[1]);time.sleep(1)
                ui.hotkey('alt','n');ui.write(str(source),interval=.01);ui.press('enter');time.sleep(1)
                ui.screenshot().save(a.evidence/'import.png')
                ui.click(origin[0]+save[0],origin[1]+save[1]);time.sleep(1)
                ui.hotkey('alt','n');ui.hotkey('ctrl','a');ui.write(str(destination),interval=.01);ui.press('enter')
                wait(destination.exists,'GUI export',60)
                with Image.open(destination) as image:assert image.size==(80,60);image.verify()
                with Image.open(destination) as exported,Image.open(source) as original:
                    assert exported.convert('RGB').tobytes()==original.convert('RGB').tobytes(),'Export pixels changed'
                assert hashlib.sha256(source.read_bytes()).hexdigest()==before
                ui.screenshot().save(a.evidence/'export.png')
            ui.hotkey('alt','f4');proc.wait(timeout=15)
            if proc.returncode!=0:raise RuntimeError('Installed GUI did not exit cleanly')
        (a.evidence/'result.json').write_text(json.dumps(dict(passed=True,executable=a.executable,imported=str(source),exported=str(destination),original_unchanged=True,quit_relaunch=True),indent=2))
        print('PASS installed GUI open/import/export/quit/relaunch; original preserved')
    finally:
        for proc in processes:
            if proc.poll() is None:proc.terminate()
if __name__=='__main__':main()
