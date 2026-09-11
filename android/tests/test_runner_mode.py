from pathlib import Path
import ast, unittest
class RunnerMode(unittest.TestCase):
    def test_instrumentation_requests_raw_status(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'test-device.py').read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and any(isinstance(a,ast.Constant) and a.value=='instrument' for a in n.args)]
        self.assertEqual(len(calls),1)
        args=[a.value for a in calls[0].args if isinstance(a,ast.Constant)]
        self.assertIn('-r',args,'raw result-code validation requires raw instrumentation output')
if __name__=='__main__': unittest.main()
