import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_provenance import artifact,audit,account_summary
from image_common import ImageError

class ProvenanceTest(unittest.TestCase):
    def test_private_preview_and_hash_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'one.wav';p.write_bytes(b'fixture')
            with self.assertRaises(ImageError):artifact(p,dict(source='upload',preview_only=True),{})
            with self.assertRaises(ImageError):artifact(p,dict(source='download',private=True),{})
            r=artifact(p,dict(source='upload'),{})
            self.assertEqual(audit(d,dict(suno=dict(artifacts=[r])))['status'],'PASS')
            p.write_bytes(b'changed');self.assertEqual(audit(d,dict(suno=dict(artifacts=[r])))['status'],'FAIL')
    def test_delayed_debit_not_double_counted(self):
        r=account_summary([dict(tool='account_usage',usage=dict(credits_remaining=100,download_credits_remaining=67)),dict(tool='sounds_create'),dict(tool='account_usage',usage=dict(credits_remaining=98,download_credits_remaining=66))])
        self.assertEqual((r['create_calls'],r['song_credits'],r['download_credits']),(1,2,1))

if __name__=='__main__':unittest.main()
