import importlib.util
from pathlib import Path
import tempfile
import unittest
import os
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('collect',ROOT/'distribution/collect.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@unittest.skipUnless(hasattr(os,'O_NOFOLLOW'),'Collector runs only on the Unix manifest job')
class CollectTests(unittest.TestCase):
    def test_both_upload_directory_layouts(self):
        for nested in [True,False]:
            with self.subTest(nested=nested),tempfile.TemporaryDirectory() as d:
                root=Path(d);source=root/'consumer-macOS-ARM64'
                if nested:source=source/'consumer'
                source.mkdir(parents=True);(source/'Filecraft.dmg').write_bytes(b'fixture')
                (source/'evidence.png').write_bytes(b'fixture')
                m.collect(root,root/'release')
                self.assertEqual([p.name for p in (root/'release').iterdir()],['Filecraft.dmg'])
    def test_duplicate_names_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ['consumer-a','consumer-b']:
                p=root/name;p.mkdir();(p/'same.dmg').write_bytes(b'fixture')
            with self.assertRaises(ValueError):m.collect(root,root/'release')
if __name__=='__main__':unittest.main()
