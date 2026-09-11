"""Static publication gates; real browser install/workflow test is separate."""
import json
from pathlib import Path
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[2]
class ExtensionPackages(unittest.TestCase):
    def test_minimal_permissions_and_static_workers(self):
        for browser in ('chromium','firefox'):
            p=ROOT/'build'/'extension'/browser
            self.assertTrue((p/'manifest.json').exists(),'Extension must be packaged')
            m=json.loads((p/'manifest.json').read_text())
            self.assertEqual(m['manifest_version'],3)
            for permission in ('permissions','host_permissions','optional_host_permissions','content_scripts','externally_connectable'):
                self.assertFalse(m.get(permission),permission)
            self.assertIn("connect-src 'none'",m['content_security_policy']['extension_pages'])
            self.assertNotIn('unsafe-eval',m['content_security_policy']['extension_pages'])
            self.assertTrue((p/'workspace/worker.js').stat().st_size>100000)
            self.assertNotIn('worker-bundle.js',(p/'workspace/index.html').read_text())
            self.assertTrue((p/'workspace/app.js').exists())
            self.assertTrue((p/'LICENSE').exists());self.assertTrue((p/'THIRD-PARTY.txt').exists())
            self.assertNotIn('update_url',m)
    def test_clean_rebuild_is_byte_identical_and_excludes_stale_files(self):
        import hashlib,subprocess,sys
        archives=[ROOT/'build'/f'Filecraft-0.10.0-beta.1-extension-{b}.zip' for b in ('chromium','firefox')]
        before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in archives]
        for browser in ('chromium','firefox'):
            (ROOT/'build/extension'/browser/'unintended-secret.txt').write_text('synthetic stale content')
        subprocess.run([sys.executable,str(ROOT/'extension/package.py')],check=True,capture_output=True)
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in archives])
        for archive in archives:
            with zipfile.ZipFile(archive) as z:self.assertNotIn('unintended-secret.txt',z.namelist())
    def test_zip_integrity_and_inventory(self):
        for browser in ('chromium','firefox'):
            with zipfile.ZipFile(ROOT/'build'/f'Filecraft-0.10.0-beta.1-extension-{browser}.zip') as z:
                self.assertIsNone(z.testzip());self.assertIn('manifest.json',z.namelist())
                self.assertTrue(all('..' not in Path(n).parts for n in z.namelist()))
