"""Output requirements must gate publication, not merely label a saved file."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from prepare_suite import core
from prepare_suite.requirements import validate_profile, evaluate, verify_receipt

class RequirementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'sensitive-name.png'
        Image.new('RGB',(120,80),'white').save(self.source)
    def request(self,profile):
        return {'source':str(self.source),'output':str(self.root/'new.png'),'target':'png','profile':profile}
    def profile(self,**constraints):
        return {'version':1,'id':'personal','constraints':constraints}
    def test_over_budget_never_published(self):
        with self.assertRaisesRegex(ValueError,'requirements'):
            core.execute(self.request(self.profile(bytes={'max':1})))
        self.assertFalse((self.root/'new.png').exists())
    def test_receipt_binds_actual_output_and_has_no_private_paths(self):
        result=core.execute(self.request(self.profile(bytes={'max':100000},formats=['png'])))
        receipt=result['receipt']; raw=json.dumps(receipt)
        self.assertNotIn('sensitive-name',raw);self.assertNotIn(str(self.root),raw)
        self.assertEqual(receipt['output']['sha256'],hashlib.sha256((self.root/'new.png').read_bytes()).hexdigest())
        self.assertEqual(receipt['readiness']['status'],'CHECKS_PASSED')
        self.assertTrue(verify_receipt(receipt,self.root/'new.png')['matches'])
        (self.root/'new.png').write_bytes(b'changed')
        self.assertFalse(verify_receipt(receipt,self.root/'new.png')['matches'])
    def test_unknown_is_not_pass(self):
        r=evaluate({'format':'txt','bytes':4,'pageCount':None,'pages':[],'filename':'x.txt'},self.profile(pageCount={'max':2}))
        self.assertEqual(r['status'],'NEEDS_REVIEW')
        self.assertEqual(r['checks'][0]['state'],'unknown')
    def test_malformed_profiles_fail_closed(self):
        for p in [self.profile(bytes={'max':True}),self.profile(bytes={'max':-1}),self.profile(bytes={'min':3,'max':2}),self.profile(typo={}),self.profile(dimensions={'unit':'mm','maxWidth':5}),{'version':2,'id':'x','constraints':{}}]:
            with self.subTest(p=p),self.assertRaises(ValueError):validate_profile(p)
    def test_page_geometry_from_output(self):
        req=self.request(self.profile(formats=['pdf'],pageCount={'max':1},orientation='landscape'))
        req.update(target='pdf',output=str(self.root/'new.pdf'))
        result=core.execute(req)
        self.assertEqual(result['receipt']['output']['pageCount'],1)
        self.assertEqual(result['receipt']['readiness']['status'],'CHECKS_PASSED')
    def test_receipt_validation_rejects_malformed_or_unbounded(self):
        with self.assertRaises(ValueError):verify_receipt({'version':1,'output':{'sha256':'invalid','bytes':3}},self.source)
    def test_filename_constraint_uses_export_filename(self):
        with self.assertRaisesRegex(ValueError,'requirements'):
            core.execute(self.request(self.profile(filename={'extensions':['pdf']})))
        self.assertFalse((self.root/'new.png').exists())
    def test_verifier_rejects_symlink_substituted_after_path_check(self):
        from unittest.mock import patch
        original=core.regular
        alternate=self.root/'alternate.png';alternate.write_bytes(self.source.read_bytes())
        proof=core.execute(self.request(self.profile()))['receipt']
        target=self.root/'new.png'
        def swap(path):
            checked=original(path);checked.unlink();checked.symlink_to(alternate);return checked
        with patch('prepare_suite.core.regular',side_effect=swap):
            with self.assertRaises((ValueError,OSError)):verify_receipt(proof,target)
    def test_no_profile_still_returns_receipt_without_certification(self):
        req=self.request(self.profile());req.pop('profile')
        result=core.execute(req)
        self.assertEqual(result['receipt']['readiness']['status'],'NEEDS_REVIEW')
        self.assertFalse(result['receipt']['visualReviewVerified'])

if __name__=='__main__':unittest.main()
