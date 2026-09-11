import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ENTRY=Path(__file__).resolve().parents[1]/'launch.py'
class WorkerTests(unittest.TestCase):
    def test_real_worker_pipe_request(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';Image.new('RGB',(20,10),'blue').save(source)
            output=Path(td)/'new.jpg'
            result=subprocess.run([sys.executable,str(ENTRY),'--worker'],input=json.dumps({'source':str(source),'output':str(output),'target':'jpg'}),text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['ok'])
            self.assertTrue(output.exists())
    def test_invalid_request_does_not_dump_traceback(self):
        result=subprocess.run([sys.executable,str(ENTRY),'--worker'],input='{}',text=True,capture_output=True,timeout=30)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertNotIn('Traceback',result.stderr)

if __name__=='__main__':unittest.main()
