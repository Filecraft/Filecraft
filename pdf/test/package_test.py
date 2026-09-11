"""Run with python3 -m unittest discover -s pdf/test -p '*_test.py'."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

PDF = Path(__file__).resolve().parents[1]

class Packaging(unittest.TestCase):
    def test_deterministic_standalone_archive(self):
        self.assertTrue((PDF / 'package.py').is_file(), 'package.py must exist')
        spec=importlib.util.spec_from_file_location('pdf_package',PDF/'package.py')
        assert spec is not None and spec.loader is not None
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); first=module.build(root/'a'); second=module.build(root/'b')
            self.assertEqual(first.read_bytes(),second.read_bytes())
            self.assertLess(first.stat().st_size,2_000_000)
            with zipfile.ZipFile(first) as archive:
                names=set(archive.namelist())
                for name in ['LICENSE','pdf/README.md','pdf/cli.cjs','pdf/worker.cjs','pdf/document.js','pdf/vendor/pdf-lib.min.js','pdf/vendor/LICENSE.pdf-lib','pdf/vendor/PROVENANCE.json','pdf/test/core.test.cjs','pdf/package.py']:
                    self.assertIn(name,names)
                self.assertFalse(any('node_modules/' in n or '/dist/' in n or '__pycache__' in n for n in names))
                archive.extractall(root/'unpacked')
            result=subprocess.run(['node','pdf/cli.cjs','--version'],cwd=root/'unpacked',capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('1.17.1',result.stdout)
            tests=subprocess.run(['node','--test','pdf/test/core.test.cjs','pdf/test/cli.test.cjs','pdf/test/geometry.test.cjs'],cwd=root/'unpacked',capture_output=True,text=True,timeout=40)
            self.assertEqual(tests.returncode,0,tests.stdout+tests.stderr)
            self.assertIn(hashlib.sha256(first.read_bytes()).hexdigest(),first.with_suffix('.zip.sha256').read_text())

if __name__=='__main__': unittest.main()
