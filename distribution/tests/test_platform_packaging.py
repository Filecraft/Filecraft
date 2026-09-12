"""Portable regressions; native install tests are separate release gates."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(platform):
    path = ROOT / 'distribution' / platform / 'build.py'
    spec = importlib.util.spec_from_file_location('pack_' + platform, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LinuxPackaging(unittest.TestCase):
    def test_linux_contract(self):
        path = ROOT / 'distribution/linux/build.py'
        self.assertTrue(path.exists(), 'Linux packaging implementation missing')
        module = load('linux')
        self.assertEqual(module.VERSION, json.loads((ROOT/'product.json').read_text())['version'])
        self.assertEqual(module.DEB_VERSION, module.VERSION.replace('-beta.', '~beta.')+'-1')
        self.assertIn('libxss1', module.DEPENDS)
        self.assertIn('libxft2', module.DEPENDS)
        self.assertIn('libx11-6', module.DEPENDS)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                module.validate_bundle(Path(td))
        source = path.read_text()
        self.assertIn('--root-owner-group', source)
        self.assertNotIn('postinst', source)
        self.assertNotIn('rmtree', source)
        desktop = (ROOT / 'distribution/linux/io.filecraft.Filecraft.desktop').read_text()
        self.assertIn('Exec=/usr/bin/filecraft', desktop)
        self.assertIn('Terminal=false', desktop)
        self.assertNotIn('MimeType=', desktop)


class WindowsPackaging(unittest.TestCase):
    def test_windows_contract(self):
        folder = ROOT / 'distribution/windows'
        self.assertTrue((folder / 'build.py').exists(), 'Windows packaging implementation missing')
        module = load('windows')
        self.assertEqual(module.VERSION, json.loads((ROOT/'product.json').read_text())['version'])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                module.validate_bundle(Path(td))
        setup = (folder / 'filecraft.iss').read_text()
        for value in ('PrivilegesRequired=lowest', 'DefaultDirName={localappdata}\\Programs\\Filecraft', 'AppId=Filecraft.Desktop', 'Uninstallable=yes', 'SignedUninstaller=no'):
            self.assertIn(value, setup)
        self.assertNotIn('[Registry]', setup)
        self.assertNotIn('[UninstallDelete]', setup)
        launcher = (folder / 'launcher.c').read_text()
        self.assertIn('CREATE_NO_WINDOW', launcher)
        self.assertIn('CreateProcessW', launcher)
        self.assertNotIn('ShellExecute', launcher)
        self.assertIn('/SUBSYSTEM:WINDOWS', (folder / 'build.py').read_text())


class NativeGateContracts(unittest.TestCase):
    def test_native_gates_are_explicit(self):
        windows = ROOT / 'distribution/windows/test-install.ps1'
        linux = ROOT / 'distribution/linux/test-install.py'
        self.assertTrue(windows.exists(), 'Windows native gate missing')
        self.assertTrue(linux.exists(), 'Linux native gate missing')
        win = windows.read_text()
        for token in ('MainWindowHandle', 'CloseMainWindow', 'check_frozen.py', 'unins000.exe', 'Get-FileHash'):
            self.assertIn(token, win)
        lin = linux.read_text()
        for token in ('--fsys-tarfile', '--ctrl-tarfile', 'check_frozen.py', "'--remove'", "'--install'"):
            self.assertIn(token, lin)


class BundleSafety(unittest.TestCase):
    def fixture(self, root, target):
        (root / '_internal').mkdir()
        (root / 'licenses').mkdir()
        for name in ('FILECRAFT-LICENSE', 'FILECRAFT-NOTICE', 'DEPENDENCIES.json', 'OPENSSL-PROVENANCE.json'):
            (root / 'licenses' / name).write_text('synthetic fixture; not a release notice')
        if target == 'linux':
            header = bytearray(20)
            header[:6] = b'\x7fELF\x02\x01'
            header[18:20] = b'\x3e\x00'
            name = 'Filecraft-Desktop'
        else:
            header = bytearray(70)
            header[:2] = b'MZ'
            header[60:64] = (64).to_bytes(4, 'little')
            header[64:70] = b'PE\0\0\x64\x86'
            name = 'Filecraft-Desktop.exe'
        (root / name).write_bytes(header)

    def test_preserves_input_and_rejects_escape(self):
        for target in ('linux', 'windows'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self.fixture(root, target)
                module = load(target)
                exe = module.validate_bundle(root)
                before = exe.read_bytes()
                self.assertEqual(module.sha256(exe), __import__('hashlib').sha256(before).hexdigest())
                self.assertEqual(exe.read_bytes(), before)
                try:
                    (root / 'escape').symlink_to(root.parent)
                except OSError:
                    continue # Windows unprivileged symlink creation may be unavailable.
                with self.assertRaises(ValueError):
                    module.validate_bundle(root)


if __name__ == '__main__':
    unittest.main()
