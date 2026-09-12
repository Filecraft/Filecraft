"""Release validation must reject partial, stale and corrupted artifacts."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('manifest',ROOT/'distribution/manifest.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ManifestTests(unittest.TestCase):
    def fixture(self,p):
        a=p/'Filecraft-0.10.0-beta.2-macos-arm64.dmg';a.write_bytes(b'test fixture, never published')
        h=hashlib.sha256(a.read_bytes()).hexdigest()
        a.with_name(a.name+'.sha256').write_text(h+'  '+a.name+'\n')
        return dict(product='Filecraft',version='0.10.0-beta.2',channel='beta',platform='macos',architecture='arm64',artifact_type='dmg',filename=a.name,bytes=a.stat().st_size,sha256=h,signing='ad-hoc',notarization='not-notarized',classification='consumer',installation=['Open DMG'])
    def test_valid_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.fixture(p);m.validate_artifact(p,a,'0.10.0-beta.2')
    def test_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.fixture(p)
            for key,value in [('version','0.9.0'),('bytes',1),('sha256','0'*64),('filename','../escape.dmg'),('architecture','universal'),('notarization','notarized'),('signing','trusted')]:
                with self.subTest(key=key),self.assertRaises(ValueError):m.validate_artifact(p,{**a,key:value},'0.10.0-beta.2')
            (p/a['filename']).write_bytes(b'partial')
            with self.assertRaises(ValueError):m.validate_artifact(p,a,'0.10.0-beta.2')
    def test_missing_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.fixture(p);(p/(a['filename']+'.sha256')).unlink()
            with self.assertRaises(ValueError):m.validate_artifact(p,a,'0.10.0-beta.2')
    def test_partial_matrix_rejected(self):
        with self.assertRaises(ValueError):m.validate_matrix([])
    def test_duplicate_matrix_rejected(self):
        a=dict(platform='macos',architecture='arm64',artifact_type='dmg')
        with self.assertRaises(ValueError):m.validate_matrix([a,a])
    def test_peels_remote_tag_and_rejects_mismatch(self):
        from unittest.mock import patch
        commit='a'*40;tag='b'*40
        responses=[json.dumps({'object':{'type':'tag','sha':tag}}),json.dumps({'object':{'type':'commit','sha':commit}})]
        with patch.object(m.subprocess,'check_output',side_effect=responses):
            self.assertEqual(m.resolve_tag('v0.10.0-beta.2'),commit)
        with patch.object(m.subprocess,'check_output',return_value=json.dumps({'object':{'type':'commit','sha':commit}})):
            self.assertEqual(m.resolve_tag('v0.10.0-beta.2'),commit)
        with patch.object(m,'resolve_tag',return_value=commit):
            with self.assertRaisesRegex(ValueError,'source'):
                m.verify_source({'tag':'v0.10.0-beta.2','version':'0.10.0-beta.2','source_commit':'c'*40})
    def test_public_partial_matrix_rejected_before_network(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d, patch.object(m.subprocess,'check_output',return_value=json.dumps({'draft':False,'published_at':'2026-01-01','assets':[]})) as request:
            with self.assertRaisesRegex(ValueError,'matrix'):
                m.verify_public(Path(d),{'tag':'v0.10.0-beta.2','source_commit':'a'*40,'artifacts':[]})
            request.assert_not_called()

if __name__=='__main__':unittest.main()
