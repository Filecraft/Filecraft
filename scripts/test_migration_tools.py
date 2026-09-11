"""Migration safety regressions; never operate on the real site checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ReleaseSyncTests(unittest.TestCase):
    def test_origin_guard_before_network_or_writes(self):
        for remote, allowed in [
            ('https://github.com/Filecraft/filecraft.github.io.git', True),
            ('git@github.com:Filecraft/filecraft.github.io.git', True),
            ('https://github.com/personal/personal.github.io.git', False),
            ('https://github.com/Filecraft/filecraft.github.io.evil.git', False),
            (None, False),
        ]:
            with self.subTest(remote=remote), tempfile.TemporaryDirectory() as tmp:
                site = Path(tmp) / 'site'
                subprocess.run(['git', 'init', '-q', str(site)], check=True)
                if remote:
                    subprocess.run(['git', '-C', str(site), 'remote', 'add', 'origin', remote], check=True)
                marker = Path(tmp) / 'network-called'
                gh = Path(tmp) / 'gh'
                gh.write_text('#!' + sys.executable + '\nfrom pathlib import Path\n'
                              + 'Path(' + repr(str(marker)) + ').touch()\n'
                              + 'print(\'[[{"tag_name":"v0.10.0","published_at":"2026","draft":false,"html_url":"https://example.test","name":"test","prerelease":true,"assets":[]}]]\')\n')
                gh.chmod(0o755)
                for name in ('releases.json', 'downloads.json'):
                    (site / name).write_text('untouched')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/sync_releases.py'), str(site), '--current', 'v0.10.0'], env={**os.environ, 'PATH': tmp + os.pathsep + os.environ['PATH']}, capture_output=True, text=True)
                if allowed:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(marker.exists())
                    self.assertEqual(json.loads((site / 'downloads.json').read_text()), [])
                else:
                    self.assertFalse(marker.exists(), 'network ran before origin guard')
                    self.assertNotEqual(result.returncode, 0)
                    for name in ('releases.json', 'downloads.json'):
                        self.assertEqual((site / name).read_text(), 'untouched')


class ArchiveAuditTests(unittest.TestCase):
    historical = ROOT / 'build/Prepare-0.9.0-beta.1-desktop-darwin-arm64.zip'
    current = ROOT / 'build/Filecraft-0.10.0-beta.1-desktop-darwin-arm64.zip'

    def audit(self, archive):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/audit_desktop_archive.py'), str(archive)], capture_output=True, text=True)

    def test_historical_apache_archive(self):
        result = self.audit(self.historical)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)[0]['passed'])

    def test_current_archive(self):
        result = self.audit(self.current)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)[0]['passed'])

    def test_current_rejects_historical_legal_names(self):
        for suffix in ('LICENSE', 'NOTICE'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / self.current.name
                with zipfile.ZipFile(self.current) as source, zipfile.ZipFile(archive, 'w') as target:
                    for info in source.infolist():
                        name = info.filename.replace('/FILECRAFT-' + suffix, '/PREPARE-' + suffix)
                        target.writestr(name, source.read(info))
                result = self.audit(archive)
                self.assertNotEqual(result.returncode, 0)

    def test_unsupported_historical_license_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'Prepare-0.8.0-desktop-darwin-arm64.zip'
            archive.symlink_to(self.historical)
            result = self.audit(archive)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unsupported historical license line', result.stderr)


if __name__ == '__main__':
    unittest.main()
