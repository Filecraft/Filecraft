"""Qualify an installed macOS consumer DMG through real OS input.

Installs the app from the DMG under test, launches the installed bundle, and
drives a real user journey through the OS: open a document via the file
panel, export a new copy via the save panel, verify the exported pixels and
the untouched original, then quit and relaunch. Windows and Linux use
distribution/test_installed_gui.py; this is the macOS equivalent and exists
because macOS CI can only record gui_export_tested: false without it.

Input stack (each capability is proven live before use, never assumed):
- System Events (Accessibility) brings the app frontmost and parks its
  window at a known position, removing z-order ambiguity.
- Synthetic keyboard and mouse events are posted at kCGSessionEventTap --
  the same route hardware events take. PID-targeted events
  (CGEventPostToPid) are dropped by the window server for Tk apps and are
  deliberately not used.
- Panels are driven through the Go-to-Folder sheet on the Accessibility
  surface: the sheet's text field value is set and read back before it is
  committed, so navigation never depends on keystroke races. The open panel is
  given the full file path, which opens that exact file in one step, with a
  directory-plus-row fallback.
- The export button is found by its own on-screen label, OCR'd from a crop of a
  *full-screen* capture (a `screencapture -l` window capture includes the window
  shadow, which shifts pixel coordinates and misplaces clicks). The layout
  measurement only narrows the search, so a label that also appears in prose is
  not mistaken for the button.
- File panels are located with include_sheets: macOS presents them at a
  non-zero window layer (observed at layer 8), so a layer-0-only listing never
  sees them.
- A delivery probe that must receive a virtual F13 keycode (a key no human
  presses during the run) gates the whole journey, so the user's own typing
  can never be mistaken for synthetic input.

Requires macOS Accessibility permission for the host application, granted
before it started; Screen Recording permission is required (the navigation
servos off screenshots). The harness never grants itself permission, never
disables Gatekeeper and never asks for a password. Run it on an unlocked
desktop.

    python3 distribution/macos/test-installed-gui.py \
        --dmg build/qualified-beta2/release/Filecraft-0.10.0-beta.2-macos-arm64.dmg \
        --arch arm64 --source 2185272 --evidence build/gui-evidence

--dry-run performs the DMG, install, launch and calibration steps only.
--human-driven lets the human perform the journey while the harness still
verifies the bytes, quit and relaunch programmatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
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
EXPORT_WAIT_SECONDS = 120
HUMAN_WAIT_SECONDS = 300
WINDOW_X, WINDOW_Y = 260, 160
F13_KEYCODE = 105


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, **kw)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def capture_step(evidence: Path, name: str) -> str:
    """Save a screenshot of the current display as step evidence (optional)."""
    target = evidence / f'step-{name}.png'
    try:
        result = subprocess.run(['screencapture', '-x', str(target)],
                                capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
            return str(target)
    except (subprocess.SubprocessError, OSError):
        pass
    return 'unavailable'


def osascript(script: str, timeout: int = 45) -> str:
    result = subprocess.run(['osascript', '-e', script],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f'osascript failed: {result.stderr.strip()[:300]}')
    return result.stdout.strip()


def ax_place_window(pid: int, x: float, y: float) -> tuple:
    """Bring the app frontmost and park its window at (x, y) via the
    Accessibility surface (System Events), returning the confirmed frame."""
    script = ('tell application "System Events"\n'
              f'    tell (first process whose unix id is {pid})\n'
              '        set frontmost to true\n'
              '        delay 0.5\n'
              f'        set position of window 1 to {{{int(x)}, {int(y)}}}\n'
              '        delay 0.3\n'
              '        set p to position of window 1\n'
              '        set s to size of window 1\n'
              '        return ((item 1 of p) as string) & "," & (item 2 of p) & "," & '
              '(item 1 of s) & "," & (item 2 of s)\n'
              '    end tell\n'
              'end tell')
    values = osascript(script).split(',')
    return tuple(float(v) for v in values)


def ocr_text(image: Path) -> str:
    try:
        out = subprocess.run(['tesseract', str(image), 'stdout'],
                             capture_output=True, timeout=60)
        raw = out.stdout
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', 'replace')
        return raw
    except (OSError, subprocess.SubprocessError):
        return ''


def ocr_locate(image: Path, needle: str, panel_only: bool = True):
    """Return the logical-screen centre of the first OCR match, or None.
    Panel-only restricts to the open panel's column area."""
    try:
        out = subprocess.run(['tesseract', str(image), 'stdout', 'tsv'],
                             capture_output=True, timeout=60)
        tsv = out.stdout.decode('utf-8', 'replace') if isinstance(out.stdout, bytes) else out.stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in tsv.splitlines()[1:]:
        parts = line.split('\t')
        if len(parts) == 12 and parts[11].strip():
            x, y, w, h = (int(parts[i]) for i in (6, 7, 8, 9))
            lx, ly = (x + w / 2) / 2.0, (y + h / 2) / 2.0  # screenshots are 2x
            if panel_only and not (lx > 430 and 180 < ly < 620):
                continue
            if needle.lower() in parts[11].strip().lower():
                return (lx, ly)
    return None


class QuartzDriver:
    """Synthetic input posted at the session event tap."""

    def __init__(self):
        import Quartz  # noqa: PLC0415 - imported late so --help works without pyobjc
        from AppKit import NSRunningApplication  # noqa: PLC0415
        self.q = Quartz
        self._nsapp = NSRunningApplication

    def activate(self, pid: int):
        app = self._nsapp.runningApplicationWithProcessIdentifier_(pid)
        app.activateWithOptions_(1)

    def window_bounds(self, pid: int, include_sheets: bool = False):
        """On-screen windows owned by pid.

        include_sheets is required for file panels: macOS presents them as
        sheets at a non-zero window layer (observed at layer 8), so a
        layer-0-only listing never sees the open or save panel at all.
        """
        listing = self.q.CGWindowListCopyWindowInfo(
            self.q.kCGWindowListOptionOnScreenOnly | self.q.kCGWindowListExcludeDesktopElements,
            self.q.kCGNullWindowID)
        found = []
        for window in listing:
            if window.get('kCGWindowOwnerPID') != pid:
                continue
            if not include_sheets and window.get('kCGWindowLayer') != 0:
                continue
            bounds = dict(window['kCGWindowBounds'])
            found.append(({key: bounds[key] for key in ('X', 'Y', 'Width', 'Height')},
                          window.get('kCGWindowName'), window.get('kCGWindowNumber')))
        return found

    def wait_window(self, pid: int, seconds: float = WINDOW_POLL_SECONDS, minimum: int = 1):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            windows = self.window_bounds(pid)
            if len(windows) >= minimum:
                return windows
            time.sleep(0.2)
        return []

    def click(self, point, double=False):
        q = self.q
        move = q.CGEventCreateMouseEvent(None, q.kCGEventMouseMoved, point, q.kCGMouseButtonLeft)
        q.CGEventPost(q.kCGSessionEventTap, move)
        time.sleep(0.15)
        clicks = (1, 1) if not double else (1, 2)
        for click_state in clicks:
            for kind in (q.kCGEventLeftMouseDown, q.kCGEventLeftMouseUp):
                event = q.CGEventCreateMouseEvent(None, kind, point, q.kCGMouseButtonLeft)
                q.CGEventSetIntegerValueField(event, q.kCGMouseEventClickState, click_state)
                q.CGEventPost(q.kCGSessionEventTap, event)
                time.sleep(0.08)
            if click_state == 1 and double:
                time.sleep(0.15)

    def key(self, code: int, flags: int = 0):
        for down in (True, False):
            event = self.q.CGEventCreateKeyboardEvent(None, code, down)
            if flags:
                self.q.CGEventSetFlags(event, flags)
            self.q.CGEventPost(self.q.kCGSessionEventTap, event)
            time.sleep(0.04)

    def text(self, value: str):
        event = self.q.CGEventCreateKeyboardEvent(None, 0, True)
        self.q.CGEventKeyboardSetUnicodeString(event, len(value), value)
        self.q.CGEventPost(self.q.kCGSessionEventTap, event)
        time.sleep(0.05)
        up = self.q.CGEventCreateKeyboardEvent(None, 0, False)
        self.q.CGEventPost(self.q.kCGSessionEventTap, up)


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
    activates it and posts a virtual F13 keycode at the session tap. Only a
    delivered F13 proves synthetic input; any other key could be the user's
    own typing if the probe window took focus, so it is never evidence.
    """
    script = (
        "import json,sys,tkinter as tk\n"
        "out=sys.argv[1]\n"
        "got=[]\n"
        "root=tk.Tk();root.title('Filecraft delivery probe');root.geometry('240x120+120+120')\n"
        "root.bind('<Key>',lambda e:(got.append(e.keysym),open(out,'w').write(json.dumps(got))))\n"
        "root.after(15000,root.destroy);root.update();root.mainloop()\n"
    )
    out = Path(tempfile.mkdtemp()) / 'received.json'
    proc = subprocess.Popen([sys.executable, '-c', script, str(out)])
    try:
        if driver.wait_window(proc.pid, seconds=15):
            time.sleep(0.6)
            driver.activate(proc.pid)
            time.sleep(0.8)
            for _ in range(3):
                driver.key(F13_KEYCODE)
                time.sleep(0.4)
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
    return {'delivered': 'F13' in received, 'f13_count': received.count('F13'),
            'received': received[:10]}


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

    def save() -> None:
        """Persist the record after every step, so a slow, interrupted or
        timed-out run still leaves the evidence it actually gathered."""
        (args.evidence / 'result.json').write_text(
            json.dumps(record, indent=2, default=str) + '\n')

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
        'screenshots': {},
    }
    if not args.dmg.exists():
        record['status'] = 'FAILED: DMG not found'
        (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(record['status'])
        return 2

    try:
        import Quartz  # noqa: F401
        import AppKit  # noqa: F401
    except ImportError:
        record['status'] = 'FAILED: pyobjc Quartz/AppKit unavailable in this interpreter'
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
    record['preflight_note'] = ('preflight can be stale after a host restart; the live delivery '
                                'probe below is the capability gate')
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
        save()

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
        save()

        samples = args.evidence / 'samples'
        samples.mkdir(exist_ok=True)
        source_image = samples / 'source.png'
        destination = samples / f'export-{time.time_ns()}.png'
        from PIL import Image  # noqa: PLC0415
        Image.new('RGB', (80, 60), '#b54120').save(source_image)
        before = sha256(source_image)

        def launch():
            proc = subprocess.Popen([str(binary)], cwd=str(samples.resolve()),
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            bounds = driver.wait_window(proc.pid)
            if not bounds:
                raise RuntimeError('installed app produced no window')
            time.sleep(0.8)
            frame = ax_place_window(proc.pid, WINDOW_X, WINDOW_Y)
            return proc, frame

        def screenshot() -> Path:
            path = args.evidence / f'step-{time.time_ns()}.png'
            subprocess.run(['screencapture', '-x', str(path)], capture_output=True, timeout=15)
            return path

        def se_keystroke(pid: int, text: str, command: bool = False,
                         shift: bool = False, timeout: int = 45):
            """Type into the app via System Events (Accessibility surface)."""
            mods = (['command down'] if command else []) + (['shift down'] if shift else [])
            mod = ' using {' + ', '.join(mods) + '}' if mods else ''
            script = ('tell application "System Events"\n'
                      f'    tell (first process whose unix id is {pid})\n'
                      '        set frontmost to true\n'
                      '        delay 0.3\n'
                      f'        keystroke "{text}"{mod}\n'
                      '    end tell\n'
                      'end tell')
            osascript(script, timeout=timeout)

        def se_key_code(code: int, timeout: int = 45):
            osascript(f'tell application "System Events" to key code {code}',
                      timeout=timeout)

        def capture_window(win, name: str) -> Path:
            """Occlusion-proof capture of a single window (id in win[2])."""
            path = args.evidence / f'step-{name}.png'
            subprocess.run(['screencapture', '-x', f'-l{win[2]}', str(path)],
                           capture_output=True, timeout=15)
            return path

        def win_ocr_first(win, needle: str, attempts: int = 4):
            """Locate needle inside one window via OCR of its own image;
            return the global click point (screen coordinates) or None."""
            from PIL import Image  # noqa: PLC0415
            frame = win[0]
            for attempt in range(attempts):
                path = capture_window(win, f'ocr-{needle.replace(".", "-")}-{attempt}')
                if not path.exists() or path.stat().st_size == 0:
                    time.sleep(1.2)
                    continue
                try:
                    img_w = Image.open(path).size[0]
                except OSError:
                    return None
                try:
                    out = subprocess.run(['tesseract', str(path), 'stdout', 'tsv'],
                                         capture_output=True, timeout=60)
                    tsv = out.stdout.decode('utf-8', 'replace') if isinstance(out.stdout, bytes) else out.stdout
                except (OSError, subprocess.SubprocessError):
                    return None
                hits = []
                for line in tsv.splitlines()[1:]:
                    parts = line.split('\t')
                    if len(parts) == 12 and parts[11].strip() and needle.lower() in parts[11].strip().lower():
                        x, y, w, h = (int(parts[i]) for i in (6, 7, 8, 9))
                        hits.append((x + w / 2, y + h / 2))
                if hits and img_w and frame['Width']:
                    px_scale = float(img_w) / float(frame['Width'])
                    px, py = hits[-1]
                    return (frame['X'] + px / px_scale, frame['Y'] + py / px_scale)
                time.sleep(1.2)
            return None

        def screen_scale_factor() -> float:
            """Backing scale: display pixels per point (2.0 on Retina hosts).

            Needed because a full-screen capture is in pixels while window
            frames and CGEvent coordinates are in points."""
            points = driver.q.CGDisplayBounds(driver.q.CGMainDisplayID()).size.width
            shot = args.evidence / 'scale-probe.png'
            subprocess.run(['screencapture', '-x', str(shot)], capture_output=True, timeout=15)
            try:
                from PIL import Image  # noqa: PLC0415
                with Image.open(shot) as img:
                    width = img.size[0]
            except (OSError, ImportError):
                return 1.0
            # CGDisplayPixelsWide reports points on current macOS, so the scale
            # is measured from a real capture: pixels per point (2.0 on Retina).
            return float(width) / float(points) if points else 1.0

        def screen_ocr_in(frame, needle: str, attempts: int = 3, near=None):
            """Global click point of needle inside a known window frame.

            Deliberately OCRs a crop of a *full-screen* capture rather than a
            `screencapture -l` window capture: window captures include the
            window shadow, which shifts every pixel coordinate and silently
            misplaces synthetic clicks. Screen captures carry no such offset.
            """
            from PIL import Image  # noqa: PLC0415
            factor = screen_scale_factor()
            for _ in range(attempts):
                shot = args.evidence / f'screen-{time.time_ns()}.png'
                subprocess.run(['screencapture', '-x', str(shot)], capture_output=True, timeout=15)
                if not shot.exists() or shot.stat().st_size == 0:
                    time.sleep(1.2)
                    continue
                crop_path = shot.with_name(shot.stem + '-crop.png')
                with Image.open(shot) as img:
                    box = (int(frame['X'] * factor), int(frame['Y'] * factor),
                           int((frame['X'] + frame['Width']) * factor),
                           int((frame['Y'] + frame['Height']) * factor))
                    img.crop(box).save(crop_path)
                out = subprocess.run(['tesseract', str(crop_path), 'stdout', 'tsv'],
                                     capture_output=True, timeout=60)
                tsv = (out.stdout.decode('utf-8', 'replace')
                       if isinstance(out.stdout, bytes) else out.stdout)
                hits = []
                for line in tsv.splitlines()[1:]:
                    parts = line.split('\t')
                    if (len(parts) == 12 and parts[11].strip()
                            and needle.lower() in parts[11].strip().lower()):
                        x, y, w, h = (int(parts[i]) for i in (6, 7, 8, 9))
                        hits.append((x + w / 2, y + h / 2))
                if hits:
                    if near is not None:
                        # Several labels can contain the same word (a button and
                        # a sentence in a disclaimer); pick the match nearest the
                        # approximate location the layout measurement predicted.
                        hint = ((near[0] - frame['X']) * factor,
                                (near[1] - frame['Y']) * factor)
                        px, py = min(hits, key=lambda h: (h[0] - hint[0]) ** 2 +
                                     (h[1] - hint[1]) ** 2)
                    else:
                        px, py = hits[-1]
                    return (frame['X'] + px / factor, frame['Y'] + py / factor)
                time.sleep(1.2)
            return None

        def panel_goto(pid: int, directory: Path):
            """Drive the Go-to-Folder sheet of the frontmost open/save panel:
            the sheet's text field is set and read back over Accessibility
            before it is committed, so a keystroke race can never send the
            panel to a stale pre-filled path."""
            se_keystroke(pid, 'g', command=True, shift=True)
            time.sleep(1.8)
            # The go-to sheet sits at a different depth depending on the panel:
            # the open panel's sheet hangs off a window, while the save panel is
            # itself a sheet, so its go-to sheet is nested one level deeper.
            candidates = []
            for win_idx in (1, 2, 3):
                candidates.append(f'sheet 1 of window {win_idx}')
                candidates.append(f'sheet 1 of sheet 1 of window {win_idx}')
                candidates.append(f'sheet 1 of sheet 1 of sheet 1 of window {win_idx}')
            for candidate in candidates:
                script = ('tell application "System Events"\n'
                          f'    tell (first process whose unix id is {pid})\n'
                          '        try\n'
                          f'            set sh to {candidate}\n'
                          f'            set value of text field 1 of sh to "{directory}"\n'
                          '            delay 0.4\n'
                          '            return value of text field 1 of sh\n'
                          '        on error errMsg\n'
                          '            return "ERR: " & errMsg\n'
                          '        end try\n'
                          '    end tell\n'
                          'end tell')
                value = osascript(script)
                if not value.startswith('ERR'):
                    if value != str(directory):
                        raise RuntimeError(f'goto sheet readback mismatch: {value!r}')
                    se_key_code(36)  # Return commits the sheet
                    time.sleep(3.0)
                    return
            raise RuntimeError('go-to sheet did not appear in any app window')

        def ax_select_row(pid: int, name: str) -> str:
            """Fallback: select a file row via the panel's Accessibility
            browser columns -- no screen coordinates involved at all."""
            template = (
                'tell application "System Events"\n'
                '    tell (first process whose unix id is @PID@)\n'
                '        try\n'
                '            set lst to missing value\n'
                '            try\n'
                '                set lst to list 1 of scroll area @COL@ of scroll area 1 of browser 1 of UI element 3 of UI element 1 of window 1\n'
                '            end try\n'
                '            if lst is missing value then\n'
                '                try\n'
                '                    set lst to outline 1 of scroll area @COL@ of scroll area 1 of browser 1 of UI element 3 of UI element 1 of window 1\n'
                '                end try\n'
                '            end if\n'
                '            if lst is missing value then\n'
                '                return "NOCOL"\n'
                '            end if\n'
                '            set n to count UI elements of lst\n'
                '            repeat with i from 1 to n\n'
                '                set e to UI element i of lst\n'
                '                set v to "?"\n'
                '                try\n'
                '                    set v to value of static text 1 of e as string\n'
                '                end try\n'
                '                if v is "?" then\n'
                '                    try\n'
                '                        set v to value of text field 1 of e as string\n'
                '                    end try\n'
                '                end if\n'
                '                if v is "@NAME@" then\n'
                '                    set selected of e to true\n'
                '                    return "SELECTED"\n'
                '                end if\n'
                '            end repeat\n'
                '            return "NOTFOUND"\n'
                '        on error errMsg\n'
                '            return "ERR: " & errMsg\n'
                '        end try\n'
                '    end tell\n'
                'end tell')
            for col in range(1, 9):
                script = (template.replace('@PID@', str(pid)).replace('@COL@', str(col))
                                  .replace('@NAME@', name))
                value = osascript(script, timeout=60)
                if value in ('SELECTED', 'NOTFOUND'):
                    return value
            return 'NOTFOUND'

        def click_open_button():
            """Click the Choose file button from the app's own layout."""
            point = (WINDOW_X + offsets['open'][0] / scale,
                     WINDOW_Y + (offsets['open'][1] + 28) / scale)
            driver.click(point)
            time.sleep(2.5)

        self_driver = driver

        proc, frame = launch()
        record['steps']['launch'] = {'pid': proc.pid, 'window_frame': frame}
        record['screenshots']['launch'] = capture_step(args.evidence, 'launch')
        save()

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
            proc2, frame2 = launch()
            record['steps']['relaunch'] = {'pid': proc2.pid, 'window_frame': frame2}
            print('Relaunched OK. Quit it with Cmd+Q to finish...')
            proc2.wait(timeout=HUMAN_WAIT_SECONDS)
            record['status'] = ('PASS (human-driven): installed GUI import/export, original '
                                'preserved, clean quit and relaunch; driven by the human user '
                                'because synthetic input was unavailable')
            (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
            print(record['status'])
            print('artifact sha256', record['artifact_sha256'])
            return 0

        if not record['event_delivery_probe']['delivered']:
            record['status'] = ('BLOCKED: the live delivery probe received no synthetic events, '
                                'so OS input cannot be delivered. Grant Accessibility to the host '
                                'application and restart it, then rerun, or use --human-driven.')
            proc.terminate()
            proc.wait(timeout=15)
            (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
            print(record['status'])
            return 3

        # ---- 1. open the file panel --------------------------------------
        pre_windows = {w[2] for w in driver.window_bounds(proc.pid)}
        click_open_button()
        record['steps']['open_panel_clicked'] = True
        panel_win = None
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and panel_win is None:
            for w in driver.window_bounds(proc.pid, include_sheets=True):
                if w[2] not in pre_windows and (w[1] or '').strip():
                    panel_win = w
                    break
            time.sleep(0.4)
        if panel_win is None:
            record['screenshots']['panel_failure'] = capture_step(args.evidence, 'panel-failure')
            raise RuntimeError('open panel window did not appear')
        record['steps']['open_panel_window'] = {'title': panel_win[1], 'id': panel_win[2]}
        save()

        # ---- 2. open the file --------------------------------------------
        # The Go-to-Folder sheet accepts a full file path and opens exactly
        # that file, so the file is chosen without column drilling and without
        # any guess about which column a row happens to be rendered in.
        source_target = source_image.resolve()
        panel_goto(proc.pid, source_target)
        record['steps']['panel_navigation'] = {
            'method': 'go-to sheet with the full file path (Accessibility readback)',
            'target': str(source_target)}
        save()
        time.sleep(2.0)
        se_key_code(36)  # the go-to sheet selects the file; Return opens it
        time.sleep(3.0)
        input_method = 'go-to full file path + Return'

        def document_loaded() -> bool:
            """The main window shows the loaded file and no placeholder."""
            win = next((w for w in driver.window_bounds(proc.pid) if w[2] in pre_windows), None)
            if win is None:
                return False
            text = ocr_text(capture_window(win, f'loaded-{time.time_ns()}'))
            return source_image.name in text and 'No document selected' not in text

        def wait_loaded() -> bool:
            for _ in range(6):
                if document_loaded():
                    return True
                time.sleep(1.5)
            return False

        loaded = wait_loaded()
        if not loaded:
            # Fallback: navigate to the directory, then pick the row.
            panel_goto(proc.pid, samples.resolve())
            row_point = screen_ocr_in(panel_win[0], 'source.png')
            if row_point is not None:
                record['steps']['file_row_selection'] = {'ocr': 'hit', 'point': list(row_point)}
                driver.click(row_point)  # select the row
                time.sleep(0.8)
                se_key_code(36)  # then press Open
                input_method = 'go-to directory + ocr row select + Open'
            else:
                selected = ax_select_row(proc.pid, 'source.png')
                record['steps']['file_row_selection'] = {'ocr': 'missed', 'accessibility': selected}
                if selected != 'SELECTED':
                    record['screenshots']['row_failure'] = str(
                        capture_window(panel_win, 'row-failure'))
                    raise RuntimeError(f'source.png row not selectable: {selected}')
                input_method = 'go-to directory + accessibility selection + Return'
                se_key_code(36)
            time.sleep(3.0)
            loaded = wait_loaded()
        if not loaded:
            record['screenshots']['import_failure'] = capture_step(args.evidence, 'import-failure')
            raise RuntimeError('document import not visually confirmed')
        record['steps']['gui_import_navigation'] = {'method': input_method, 'navigated': True}
        record['steps']['gui_import'] = {'filename_visible': True, 'placeholder_gone': True}
        save()

        # ---- 4. export: click the export button, drive the save panel -----
        # The export button is found by its own on-screen label. A measured
        # offset is only the fallback: the layout differs once a document is
        # loaded, and a stale offset clicks the wrong widget silently.
        main_win = next((w for w in driver.window_bounds(proc.pid) if w[2] in pre_windows), None)
        measured_export = (WINDOW_X + offsets['save'][0] / scale,
                           WINDOW_Y + (offsets['save'][1] + 28) / scale)
        export_point = (screen_ocr_in(main_win[0], 'Export', near=measured_export)
                        if main_win else None)
        if export_point is None:
            export_point = measured_export
            record['steps']['export_button'] = {'located': 'measured offset (label not found)'}
        else:
            record['steps']['export_button'] = {'located': 'on-screen label',
                                                'point': list(export_point)}
        driver.click(export_point)
        time.sleep(2.5)
        record['screenshots']['save_panel'] = capture_step(args.evidence, 'save-panel')
        save()

        def save_panel_attempt() -> None:
            # The save panel's name field is focused by default; replace the
            # suggested name, then save into the remembered directory.
            se_keystroke(proc.pid, 'a', command=True)
            time.sleep(0.4)
            se_keystroke(proc.pid, destination.name)
            time.sleep(0.6)
            se_key_code(36)  # Return = Save
            time.sleep(2.5)

        def resolve_export():
            """The saved file, allowing for the extension the save panel adds.

            A save panel given a name that already ends in the chosen format's
            extension appends it again, so the real output can be either the
            requested path or that path with one more extension.
            """
            for candidate in (destination, samples / (destination.name + destination.suffix)):
                if candidate.exists():
                    return candidate
            return None

        produced = None
        save_panel_attempt()
        deadline = time.monotonic() + EXPORT_WAIT_SECONDS
        while produced is None and time.monotonic() < deadline:
            produced = resolve_export()
            if produced is None:
                time.sleep(1.0)
        if produced is None:
            # Fall back to naming the full destination path through the save
            # panel's go-to sheet, which sets folder and name in one step.
            try:
                panel_goto(proc.pid, destination)
                time.sleep(1.5)
                se_key_code(36)  # Save
            except RuntimeError:
                panel_goto(proc.pid, samples.resolve())
                save_panel_attempt()
            for _ in range(20):
                produced = resolve_export()
                if produced is not None:
                    break
                time.sleep(1.0)
        if produced is None:
            record['screenshots']['export_failure'] = capture_step(args.evidence, 'export-failure')
            raise RuntimeError('GUI export produced no file')
        destination = produced
        record['steps']['export_file'] = {'path': str(destination),
                                          'bytes': destination.stat().st_size}
        save()

        with Image.open(destination) as exported, Image.open(source_image) as original:
            assert exported.size == (80, 60), exported.size
            assert exported.convert('RGB').tobytes() == original.convert('RGB').tobytes(), 'export pixels changed'
        assert sha256(source_image) == before, 'original file changed'
        record['steps']['gui_import_export'] = {'exported': str(destination), 'pixels_equal': True,
                                                'original_unchanged': True}

        # ---- 5. quit and relaunch ----------------------------------------
        def quit_via_cmd_q(p) -> int:
            try:
                se_keystroke(p.pid, 'q', command=True)
            except RuntimeError:
                pass
            try:
                p.wait(timeout=12)
            except subprocess.TimeoutExpired:
                # Cmd+Q never took effect: that is a qualification failure,
                # not something to paper over with a synthetic success.
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=10)
            return p.returncode

        record['steps']['quit'] = {'returncode': quit_via_cmd_q(proc)}
        save()
        assert record['steps']['quit']['returncode'] == 0, record['steps']['quit']

        proc2, frame2 = launch()
        record['steps']['relaunch'] = {'pid': proc2.pid, 'window_frame': frame2}
        save()
        time.sleep(1.5)
        record['steps']['relaunch_quit'] = {'returncode': quit_via_cmd_q(proc2)}
        assert record['steps']['relaunch_quit']['returncode'] == 0, record['steps']['relaunch_quit']

        record['status'] = ('PASS: installed GUI import/export, original preserved, clean quit and '
                            'relaunch through OS input')
        (args.evidence / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(record['status'])
        print('artifact sha256', record['artifact_sha256'])
        return 0
    except Exception as error:  # noqa: BLE001 - recorded as evidence, never swallowed silently
        record['status'] = f'FAILED: {type(error).__name__}: {error}'
        save()
        print(record['status'])
        return 1
    finally:
        if mount:
            subprocess.run(['hdiutil', 'detach', str(mount)], capture_output=True)


if __name__ == '__main__':
    sys.exit(main())
