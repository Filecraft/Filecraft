import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('packaging',ROOT/'desktop/package.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class Compliance(unittest.TestCase):
    def test_font_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'_internal/reportlab/fonts';folder.mkdir(parents=True)
            for name in ('DarkGardenMK.pfb','DarkGarden.sfd','DarkGarden-copying.txt','Vera.ttf','bitstream-vera-license.txt'):(folder/name).write_text('fixture')
            p.prune_unused_fonts(Path(tmp))
            self.assertFalse(list(folder.glob('DarkGarden*')))
            self.assertTrue((folder/'Vera.ttf').exists())
            self.assertTrue((folder/'bitstream-vera-license.txt').exists())
    def test_unknown_tls_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(p,'openssl_versions',return_value={'python':'LibreSSL 2.8.3'}):
            with self.assertRaisesRegex(RuntimeError,'unsupported TLS'):
                p.openssl_notices(Path(tmp))

if __name__=='__main__':unittest.main()
