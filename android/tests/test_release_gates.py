"""Dependency-free release regressions; device behavior is in EngineTests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("android_build", ROOT / "build.py")
assert spec is not None
build = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(build)


verify_resources = build.verify_resources

class ReleaseGates(unittest.TestCase):
    def test_native_write_completion_is_checked_before_acceptance(self):
        # Host wiring guard complements the real PdfDocument tests on devices.
        source = (ROOT / "src/com/prepare/app/Engine.java").read_text()
        write = source.index("document.writeTo(out);")
        accept = source.index("accepted=true; return output;", write)
        self.assertIn("out.checkFailure();", source[write:accept],
                      "native write may swallow IOException; byte length is not completion")

    def test_settings_register_invalidation_listeners(self):
        source = (ROOT / "src/com/prepare/app/MainActivity.java").read_text()
        for control, listener in (("limit", "addTextChangedListener"),
                                  ("layout", "setOnItemSelectedListener"),
                                  ("margin", "setOnItemSelectedListener")):
            with self.subTest(control=control):
                self.assertIn(control + "." + listener + "(", source)

    def test_normalize_then_align_stores_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            source, raw, aligned = [Path(directory) / name for name in ("source.apk", "raw.apk", "aligned.apk")]
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("resources.arsc", b"resource payload" * 50)
                archive.writestr("AndroidManifest.xml", b"manifest")
            build.normalize(source, raw, {"classes.dex": b"dex"})
            build.run(build.TOOLS / ("zipalign" + build.EXT), "-f", "4", raw, aligned)
            verify_resources(aligned)
            with zipfile.ZipFile(aligned) as archive:
                self.assertEqual(archive.read("resources.arsc"), b"resource payload" * 50)

    def test_gate_rejects_compressed_and_unaligned_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "bad.apk"
            for method in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
                with zipfile.ZipFile(apk, "w", compression=method) as archive:
                    # Shift the local payload off its otherwise natural alignment.
                    archive.writestr("x", b"xx")
                    archive.writestr("resources.arsc", b"resource payload")
                with self.assertRaises(AssertionError):
                    verify_resources(apk)


if __name__ == "__main__":
    unittest.main()
