"""Fail-closed packaging contracts; no signing identity needed for these tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('macos_package',ROOT/'distribution/macos/package.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MacPackagingTests(unittest.TestCase):
    def test_identity_separate_from_legacy_app(self):
        info=m.bundle_info('0.10.0-beta.1','arm64')
        self.assertEqual(info['CFBundleIdentifier'],'io.github.filecraft.desktop')
        self.assertEqual(info['CFBundleExecutable'],'Filecraft-Desktop')
        self.assertEqual(info['CFBundleShortVersionString'],'0.10.0')
        self.assertNotIn('CFBundleDocumentTypes',info)
    def test_unknown_arch_rejected(self):
        with self.assertRaises(ValueError):m.bundle_info('0.10.0-beta.1','universal')
    def test_unexpected_version_rejected(self):
        with self.assertRaises(ValueError):m.bundle_info('../bad','arm64')
    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'escape').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):m.validate_tree(p)
    def test_internal_symlinks_retained(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'file').write_text('test');(p/'link').symlink_to('file');m.validate_tree(p)
    def test_absolute_internal_link_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'file').write_text('fixture');(p/'link').symlink_to(p/'file')
            with self.assertRaises(ValueError):m.validate_tree(p)
    def test_dangling_internal_link_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'link').symlink_to('absent')
            with self.assertRaises(ValueError):m.validate_tree(p)
    def test_security_label_does_not_infer_notarization(self):
        self.assertEqual(m.signature_status('Signature=adhoc\nTeamIdentifier=not set'),'ad-hoc')
        self.assertEqual(m.signature_status('code object is not signed at all'),'unsigned')
        with self.assertRaises(ValueError):m.signature_status('Authority=Unknown publisher')

if __name__=='__main__':unittest.main()
