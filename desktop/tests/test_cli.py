import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class CLITests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'launch.py'),'--cli',*args],capture_output=True,text=True,timeout=30)
    def test_prepare_then_verify_and_detect_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'original.png';out=root/'prepared.png';receipt=root/'receipt.json'
            Image.new('RGB',(20,30),'blue').save(source)
            result=self.run_cli('prepare',str(source),'--output',str(out),'--target','png','--max-bytes','100000')
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            data=json.loads(result.stdout);receipt.write_text(json.dumps(data['result']['receipt']))
            self.assertEqual(self.run_cli('verify',str(out),'--receipt',str(receipt)).returncode,0)
            Image.new('RGB',(20,30),'red').save(out)
            self.assertEqual(self.run_cli('verify',str(out),'--receipt',str(receipt)).returncode,2)
    def test_documented_direct_command_and_unknown_argument(self):
        direct=subprocess.run([sys.executable,str(ROOT/'launch.py'),'formats',str(ROOT/'tests'/'not-present.png')],capture_output=True,text=True,timeout=3)
        self.assertNotEqual(direct.returncode,0)
        self.assertIn('ok',direct.stdout)
        unknown=subprocess.run([sys.executable,str(ROOT/'launch.py'),'--nonsense'],capture_output=True,text=True,timeout=3)
        self.assertNotEqual(unknown.returncode,0)
    def test_cli_failure_does_not_publish(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';out=Path(td)/'output.png'
            Image.new('RGB',(20,30)).save(source)
            result=self.run_cli('prepare',str(source),'--output',str(out),'--target','png','--max-bytes','1')
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists());self.assertNotIn('Traceback',result.stdout+result.stderr)
