"""Qualify an installed macOS consumer DMG through real OS input.

Installs the app from the DMG under test, launches the installed bundle, drives
the file picker and the save panel with synthetic events addressed to that
process only, then checks the exported bytes, the untouched original, a clean
quit and a relaunch. Windows and Linux use distribution/test_installed_gui.py;
this is the macOS equivalent and exists because macOS CI can only record
gui_export_tested: false without it.

Requires macOS Accessibility permission for the process that runs this script
(and a process started after that grant). CGPreflightPostEventAccess can report
stale results after a host restart, so the harness does not trust it: before
the GUI journey it proves synthetic-input capability with a live delivery probe
(a Tk child that records the keys posted to its PID). It never grants itself
permission, never disables Gatekeeper and never asks for a password. Run it on
an unlocked desktop.

    python3 distribution/macos/test-installed-gui.py \
        --dmg build/qualified-beta2/release/Filecraft-0.10.0-beta.2-macos-arm64.dmg \
        --arch arm64 --source 2185272 --evidence build/gui-evidence

--dry-run performs the DMG, install, launch and coordinate-calibration steps
only, which is useful on hosts that have no Accessibility grant yet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_NAME = 'Filecraft.app'
BUNDLE_ID = 'io.github.filecraft.desktop'
EXECUTABLE = 'Contents/MacOS/Filecraft-Desktop'
WINDOW_POLL_SECONDS = 40
EXPORT_WAIT_SECONDS = 60
HUMAN_WAIT_SECONDS = 300
KEY_CMD, KEY_SHIFT, KEY_Q, KEY_G, KEY_A, KEY_HOME, KEY_END, KEY_BACKSPACE, KEY_RETURN = 55, 56, 12, 5, 0, 115, 119, 51, 36


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, **kw)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


class QuartzDriver:
    """Synthetic input addressed to one process, never to the whole desktop."""

    def __init__(self):
        import Quartz  # noqa: PLC0415 - imported late so --help works without pyobjc
        self.q = Quartz

    def window_bounds(self, pid: int):
        listing = self.q.CGWindowListCopyWindowInfo(
            self.q.kCGWindowListOptionOnScreenOnly | self.q.kCGWindowListExcludeDesktopElements,
            self.q.kCGNullWindowID)
        found = []
        for window in listing:
            if window.get('kCGWindowOwnerPID') != pid or window.get('kCGWindowLayer') != 0:
                continue
            bounds = dict(window['kCGWindowBounds'])
            found.append(({key: bounds[key] for key in ('X', 'Y', 'Width', 'Height')},
                          window.get('kCGWindowName')))
        return found

    def wait_window(self, pid: int, seconds: float = WINDOW_POLL_SECONDS, minimum: int = 1):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            windows = self.window_bounds(pid)
            if len(windows) >= minimum:
                return windows
            time.sleep(0.2)
        return []

    def click(self, pid: int, point):
        for kind in (self.q.kCGEventLeftMouseDown, self.q.kCGEventLeftMouseUp):
            event = self.q.CGEventCreateMouseEvent(None, kind, point, self.q.kCGMouseButtonLeft)
            self.q.CGEventPostToPid(pid, event)

    def key(self, pid: int, code: int, flags: int = 0):
        for down in (True, False):
            event = self.q.CGEventCreateKeyboardEvent(None, code, down)
            if flags:
                self.q.CGEventSetFlags(event, flags)
            self.q.CGEventPostToPid(pid, event)

    def text(self, pid: int, value: str):
        event = self.q.CGEventCreateKeyboardEvent(None, 0, True)
        self.q.CGEventKeyboardSetUnicodeString(event, len(value), value)
        self.q.CGEventPostToPid(pid, event)
        self.q.CGEventPostToPid(pid, self.q.CGEventCreateKeyboardEvent(None, 0, False))


def widget_offsets() -> dict:
    """Derive this version's button centres from its own layout, not constants."""
    child = f'''
import json, sys, tkinter as tk
sys.path.insert(0, {str(ROOT / "desktop")!r})
from prepare_suite.gui import App
root = tk.Tk()
app = App(root)
root.update()
def centre(widget):
    return [widget.winfo_rootx() - root.winfo_rootx() + widget.winfo_width() / 2,
            widget.winfo_rooty() - root.winfo_rooty() + widget.winfo_height() / 2]
print(json.dumps({{"open": centre(app.open_button), "save": centre(app.save_button),
                  "content": [root.winfo_width(), root.winfo_height()]}}))
root.destroy()
'''
    result = subprocess.run([sys.executable, '-c', child], check=True, capture_output=True, text=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


def measure_scale(driver: QuartzDriver) -> float:
    """Screen scale factor: CG bounds are in points, Tk geometry is in pixels."""
    child = f'''
import json, sys, tkinter as tk
root = tk.Tk()
root.geometry("300x200+120+120")
root.update()
print(json.dumps({{"w": root.winfo_width(), "h": root.winfo_height()}}), flush=True)
root.after(12000, root.destroy)
root.mainloop()
'''
    proc = subprocess.Popen([sys.executable, '-c', child], stdout=subprocess.PIPE, text=True)
    try:
        line = proc.stdout.readline()
        geometry = json.loads(line)
        bounds = None
        deadline = time.monotonic() + 10
        while bounds is None and time.monotonic() < deadline:
            found = driver.window_bounds(proc.pid)
            if found:
                bounds = found[0][0]
            else:
                time.sleep(0.2)
        if not bounds or not bounds['Width']:
            return 1.0
        return float(geometry['w']) / float(bounds['Width'])
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def probe_event_delivery(driver: QuartzDriver) -> dict:
    """Empirically verify synthetic input reaches another process.

    The preflight API can be stale for restarted hosts, so the capability gate
    is this probe: a Tk child records every key it receives while the harness
    posts a virtual keycode and a unicode string to its PID. Capability is
    proven, not assumed, and the probe's verdict is recorded as evidence.
    """
    script = (
        "import json,sys,tkinter as tk\n"
        "out=sys.argv[1]\n"
        "got=[]\n"
        "root=tk.Tk();root.title('Filecraft delivery probe');root.geometry('240x120+120+120')\n"
        "root.bind('<Key>',lambda e:got.append(e.keysym))\n"
        "def flush():open(out,'w').write(json.dumps(got))\n"
        "root.bind('<Key>',lambda e:(got.append(e.keysym),flush()))\n"
        "root.after(15000,root.destroy);root.update();root.focus_force();root.mainloop()\n"
    )
    out = Path(tempfile.mkdtemp()) / 'received.json'
    proc = subprocess.Popen([sys.executable, '-c', script, str(out)])
    try:
        if driver.wait_window(proc.pid, seconds=15):
            time.sleep(0.8)
            driver.key(proc.pid, 105)  # F13: a keycode no human presses during the run
            time.sleep(0.5)
            driver.key(proc.pid, 105)
            for _ in range(30):
                if out.exists():
                    break
                time.sleep(0.2)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    received = json.loads(out.read_text()) if out.exists() else []
    # Only a delivered F13 proves synthetic input; any other key could be the
    # user's own typing if the probe window took focus, so it is not evidence.
    return {'delivered': 'F13' in received, 'received': received}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dmg', type=Path, required=True)
    parser.add_argument('--arch', choices=['arm64', 'x86_64'], required=True)
    parser.add_argument('--source', required=True, help='Exact source commit the DMG was built from')
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--install-root', type=Path, default=Path('/Applications'))
    parser.add_argument('--translated', action='store_true',
                        help='Record that this run is Rosetta-translated, not native')
    parser.add_argument('--human-driven', action='store_true',
                        help='The human performs the GUI journey instead of synthetic events; '
                             'the harness still verifies export bytes, the untouched original, '
                             'quit and relaunch programmatically')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mount, install, launch and calibrate only')
    args = parser.parse_args()

    args.evidence.mkdir(parents=True, exist_ok=True)
    record = {
        'harness': 'distribution/macos/test-installed-gui.py',
        'candidate': args.dmg.name,
        'artifact_sha256': sha256(args.dmg) if args.dmg.exists() else None,
        'artifact_bytes': args.dmg.stat().st_size if args.dmg.exists() else None,
        'source_commit': args.source,
        'architecture': args.arch,
        'integration': 'rosetta-translated' if args.translated else 'native',
        'host': run(['uname', '-m']).stdout.strip(),
        'steps': {},
        'screenshots': 'not captured: no Screen Recording permission for this process',
    }
    if not args.dmg.exists():
        record['status'] = 'FAILED: DMG not found'
        (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(record['status'])
        return 2

    try:
        import Quartz  # noqa: F401
    except ImportError:
        record['status'] = 'FAILED: pyobjc Quartz is unavailable in this interpreter'
        (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(record['status'])
        return 2

    driver = QuartzDriver()
    if hasattr(driver.q, 'CGPreflightPostEventAccess'):
        preflight = bool(driver.q.CGPreflightPostEventAccess())
    else:
        import ctypes
        preflight = bool(ctypes.cdll.LoadLibrary(
            '/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics').CGPreflightPostEventAccess())
    record['post_event_access_preflight'] = preflight
    record['event_delivery_probe'] = probe_event_delivery(driver)

    installed = args.install_root / APP_NAME
    mount = None
    try:
        info = plistlib.loads(subprocess.check_output(
            ['hdiutil', 'attach', '-readonly', '-nobrowse', '-plist', str(args.dmg)]))
        mount = next(Path(e['mount-point']) for e in info['system-entities'] if 'mount-point' in e)
        assert (mount / 'Applications').is_symlink() and (mount / 'Applications').readlink() == Path('/Applications')
        assert (mount / '.DS_Store').is_file()
        record['steps']['dmg_layout'] = 'Applications symlink and Finder layout present'

        leftover = subprocess.run(['pgrep', '-f', str(installed)], capture_output=True, text=True).stdout.split()
        for pid in leftover:
            os.kill(int(pid), signal.SIGTERM)
        if leftover:
            time.sleep(2)
        record['steps']['previous_instances_terminated'] = [int(p) for p in leftover]

        if installed.exists():
            backup = args.evidence / ('previous-' + APP_NAME)
            if backup.exists():
                shutil.rmtree(backup)
            run(['ditto', installed, backup])
            shutil.rmtree(installed)
            record['steps']['previous_install_backed_up'] = str(backup)
        run(['ditto', mount / APP_NAME, installed])
        run(['codesign', '--verify', '--deep', '--strict', installed])
        bundle = plistlib.loads((installed / 'Contents/Info.plist').read_bytes())
        assert bundle['CFBundleIdentifier'] == BUNDLE_ID, bundle['CFBundleIdentifier']
        record['bundle_version'] = bundle.get('CFBundleShortVersionString')
        record['bundle_build'] = bundle.get('CFBundleVersion')
        binary = installed / EXECUTABLE
        recorded_arch = run(['lipo', '-archs', binary]).stdout.strip()
        assert recorded_arch == args.arch, f'bundle is {recorded_arch}, expected {args.arch}'
        run([sys.executable, ROOT / 'desktop/check_frozen.py', binary])
        assessment = subprocess.run(['spctl', '--assess', '--type', 'execute', str(installed)],
                                    capture_output=True, text=True)
        record['steps']['installed'] = {
            'bundle_id': bundle['CFBundleIdentifier'], 'architecture': recorded_arch,
            'signature_integrity': 'codesign --verify --deep --strict passed',
            'gatekeeper_accepted': assessment.returncode == 0,
            'signing': 'ad-hoc, not notarized (per published metadata)',
        }

        offsets = widget_offsets()
        scale = measure_scale(driver)
        record['steps']['layout'] = {'button_offsets_px': offsets, 'screen_scale': scale}

        samples = args.evidence / 'samples'
        samples.mkdir(exist_ok=True)
        source_image = samples / 'source.png'
        destination = samples / f'export-{time.time_ns()}.png'
        from PIL import Image  # noqa: PLC0415
        Image.new('RGB', (80, 60), '#b54120').save(source_image)
        before = sha256(source_image)

        def launch():
            proc = subprocess.Popen([str(binary)])
            bounds = driver.wait_window(proc.pid)
            if not bounds:
                raise RuntimeError('installed app produced no window')
            return proc, bounds

        proc, bounds = launch()
        record['steps']['launch'] = {'pid': proc.pid, 'window_bounds': bounds[0][0],
                                     'windows_visible': len(bounds)}

        if args.dry_run:
            proc.terminate()
            proc.wait(timeout=15)
            record['status'] = ('DRY RUN OK: mount, install, launch and calibration verified; '
                                'synthetic input not attempted')
            (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
            print(json.dumps(record['steps']['installed'], indent=2))
            print(record['status'])
            return 0

        if args.human_driven:
            record['input_driver'] = 'human'
            destination = samples / f'export-human-{args.arch}-{time.time_ns()}.png'
            print('HUMAN-DRIVEN MODE: perform the journey in the visible Filecraft window:')
            print(f'  1. Click Open and pick this file: {source_image}')
            print(f'  2. Click Save/Export and save exactly to: {destination}')
            print('     (in the save panel press Cmd+Shift+G to type the path)')
            print('  3. Quit with Cmd+Q; the harness relaunches, then quit that too.')
            deadline = time.monotonic() + HUMAN_WAIT_SECONDS
            while not destination.exists() and time.monotonic() < deadline:
                time.sleep(1.0)
            if not destination.exists():
                raise RuntimeError('human-driven export produced no file')
            with Image.open(destination) as exported, Image.open(source_image) as original:
                assert exported.size == (80, 60), exported.size
                assert exported.convert('RGB').tobytes() == original.convert('RGB').tobytes(), 'export pixels changed'
            assert sha256(source_image) == before, 'original file changed'
            record['steps']['gui_import_export'] = {'exported': str(destination), 'pixels_equal': True,
                                                    'original_unchanged': True, 'input_driver': 'human'}
            print('Export verified. Quit the app with Cmd+Q now...')
            proc.wait(timeout=HUMAN_WAIT_SECONDS)
            assert proc.returncode == 0, proc.returncode
            record['steps']['quit'] = {'returncode': proc.returncode, 'driver': 'human'}
            proc2, bounds2 = launch()
            record['steps']['relaunch'] = {'pid': proc2.pid, 'window_bounds': bounds2[0][0]}
            print('Relaunched OK. Quit it with Cmd+Q to finish...')
            proc2.wait(timeout=HUMAN_WAIT_SECONDS)
            record['status'] = ('PASS (human-driven): installed GUI import/export, original '
                                'preserved, clean quit and relaunch; driven by the human user '
                                'because synthetic input was unavailable')
            (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
            print(record['status'])
            print('artifact sha256', record['artifact_sha256'])
            return 0

        if not record['event_delivery_probe']['delivered'] and not args.human_driven:
            record['status'] = ('BLOCKED: the live delivery probe received no synthetic events, '
                                'so OS input cannot be delivered. Grant Accessibility to the host '
                                'application and restart it, then rerun, or use --human-driven.')
            proc.terminate()
            proc.wait(timeout=15)
            (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
            print(record['status'])
            return 3

        origin = bounds[0][0]

        def press(widget, label):
            """Click a widget and confirm a dialog appeared.

            CG window bounds include the title bar while the derived offsets are
            content-relative, and Tk's frame convention is not guaranteed across
            versions, so try the plausible vertical alignments and record the one
            that actually opened a dialog instead of assuming.
            """
            baseline = len(driver.window_bounds(proc.pid))
            for title_bar in (0, 32, -32):
                point = (origin['X'] + offsets[widget][0] / scale,
                         origin['Y'] + (offsets[widget][1] + title_bar) / scale)
                driver.click(proc.pid, point)
                if driver.wait_window(proc.pid, seconds=12, minimum=baseline + 1):
                    record['steps'].setdefault('click_alignment', {})[label] = title_bar
                    return True
            return False

        if not press('open', 'file_picker'):
            raise RuntimeError('clicking the open button opened no dialog')
        time.sleep(1.0)
        driver.key(proc.pid, KEY_G, flags=driver.q.kCGEventFlagMaskCommand | driver.q.kCGEventFlagMaskShift)
        time.sleep(1.0)
        driver.text(proc.pid, str(source_image))
        time.sleep(1.0)
        driver.key(proc.pid, KEY_RETURN)
        time.sleep(1.5)
        driver.key(proc.pid, KEY_RETURN)

        if not press('save', 'save_panel'):
            raise RuntimeError('clicking the export button opened no dialog')
        time.sleep(1.2)
        driver.key(proc.pid, KEY_A, flags=driver.q.kCGEventFlagMaskCommand)
        driver.text(proc.pid, str(destination))
        time.sleep(0.8)
        driver.key(proc.pid, KEY_RETURN)

        deadline = time.monotonic() + EXPORT_WAIT_SECONDS
        while not destination.exists() and time.monotonic() < deadline:
            path_dir = destination.parent
            driver.key(proc.pid, KEY_G, flags=driver.q.kCGEventFlagMaskCommand | driver.q.kCGEventFlagMaskShift)
            time.sleep(1.0)
            driver.text(proc.pid, str(path_dir))
            driver.key(proc.pid, KEY_RETURN)
            time.sleep(1.0)
            driver.text(proc.pid, destination.name)
            time.sleep(0.5)
            driver.key(proc.pid, KEY_RETURN)
            time.sleep(2.0)
        if not destination.exists():
            raise RuntimeError('GUI export produced no file')

        with Image.open(destination) as exported, Image.open(source_image) as original:
            assert exported.size == (80, 60), exported.size
            assert exported.convert('RGB').tobytes() == original.convert('RGB').tobytes(), 'export pixels changed'
        assert sha256(source_image) == before, 'original file changed'
        record['steps']['gui_import_export'] = {'exported': str(destination), 'pixels_equal': True,
                                                'original_unchanged': True}

        driver.key(proc.pid, KEY_Q, flags=driver.q.kCGEventFlagMaskCommand)
        proc.wait(timeout=20)
        assert proc.returncode == 0, proc.returncode
        record['steps']['quit'] = {'returncode': proc.returncode}

        proc2, bounds2 = launch()
        record['steps']['relaunch'] = {'pid': proc2.pid, 'window_bounds': bounds2[0][0]}
        driver.key(proc2.pid, KEY_Q, flags=driver.q.kCGEventFlagMaskCommand)
        proc2.wait(timeout=20)

        record['status'] = ('PASS: installed GUI import/export, original preserved, clean quit and '
                            'relaunch through OS input')
        (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(record['status'])
        print('artifact sha256', record['artifact_sha256'])
        return 0
    except Exception as error:  # noqa: BLE001 - recorded as evidence, never swallowed silently
        record['status'] = f'FAILED: {type(error).__name__}: {error}'
        (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(record['status'])
        return 1
    finally:
        if mount:
            subprocess.run(['hdiutil', 'detach', str(mount)], capture_output=True)


if __name__ == '__main__':
    sys.exit(main())
