"""Run with Python 3.9+; packaging is build tooling, not a CLI dependency."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]

class PackageTests(unittest.TestCase):
    def test_source_bundle_and_checksum(self):
        spec = importlib.util.spec_from_file_location("package_engine", ROOT / "engine" / "package.py")
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as temp:
            output = mod.build(Path(temp))
            with zipfile.ZipFile(output) as z:
                self.assertIsNone(z.testzip())
                names = z.namelist()
                for needed in ["engine/cli.js", "engine/document-engine.js", "engine/inspect.js", "engine/README.md", "LICENSE"]:
                    self.assertIn(needed, names)
                self.assertFalse(any("__pycache__" in n or "/dist/" in n or n.startswith("/") or ".." in n.split("/") for n in names))
                self.assertEqual(z.read("LICENSE"), (ROOT / "LICENSE").read_bytes())
            checksum = output.with_suffix(output.suffix + ".sha256").read_text().split()[0]
            self.assertEqual(checksum, hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(output.read_bytes(), mod.build(Path(temp)).read_bytes())

if __name__ == "__main__":
    unittest.main()
