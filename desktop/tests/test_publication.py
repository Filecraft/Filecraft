import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from prepare_suite import core

class PublicationRegressions(unittest.TestCase):
    def test_competing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';dest=Path(td)/'result.jpg'
            Image.new('RGB',(20,20),'red').save(source)
            real=core.image_convert
            def race(*args):
                result=real(*args);dest.write_bytes(b'competing file');return result
            with patch.object(core,'image_convert',race),self.assertRaises(FileExistsError):
                core.execute({'source':str(source),'output':str(dest),'target':'jpg'})
            self.assertEqual(dest.read_bytes(),b'competing file')

    def test_codec_uses_snapshot_not_later_source_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.png';dest=Path(td)/'result.png'
            Image.new('RGB',(20,20),'red').save(source)
            real=core.image_convert
            def mutate(*args):
                Image.new('RGB',(20,20),'blue').save(source)
                return real(*args)
            with patch.object(core,'image_convert',mutate):
                core.execute({'source':str(source),'output':str(dest),'target':'png'})
            with Image.open(dest) as result:self.assertEqual(result.getpixel((0,0)),(255,0,0))
