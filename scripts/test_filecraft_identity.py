"""Current release identity; compatibility API names are intentionally stable."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class IdentityTests(unittest.TestCase):
    def test_current_product_and_user_interfaces(self):
        product=json.loads((ROOT/'product.json').read_text())
        self.assertEqual(product['name'],'Filecraft')
        self.assertEqual(product['repository'],'https://github.com/Filecraft/Filecraft')
        for filename in ['README.md','workbench/index.html','desktop/prepare_suite/gui.py','extension/package.py']:
            text=(ROOT/filename).read_text()
            self.assertIn('Filecraft',text,filename)
            self.assertNotIn('gonisulaimann.github.io',text,filename)
        workspace=(ROOT/'workbench/index.html').read_text()
        self.assertIn('<h1>Filecraft ',workspace)
        self.assertNotIn('0.9 beta',workspace)
    def test_ai_guidelines_and_disclosure(self):
        self.assertTrue((ROOT/'AGENTS.md').is_file())
        text=(ROOT/'docs/AI-DISCLOSURE.md').read_text()
        for token in ['$256.09','129.97M','1.84M','maintainer-supplied','not audited']:
            self.assertIn(token,text)
if __name__=='__main__':unittest.main()
