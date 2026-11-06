import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_fix_pack import next_switch_time
from audio_demo import scene


class FixPackScheduleTest(unittest.TestCase):
    def test_scene_uses_declared_switch_phase_not_unverified_wrap(self):
        self.assertEqual(next_switch_time(4000,[2000],4000),6000)
        self.assertEqual(next_switch_time(8000,[2000],4000),10000)
        with self.assertRaises(ValueError):next_switch_time(4000,[],4000)
        with tempfile.TemporaryDirectory() as folder:
            scene(Path(folder),next_switch_time(4000,[2000],4000))
            text=(Path(folder)/'demo.gd').read_text()
            self.assertIn('audio_ms >= 6000.0',text)
            self.assertNotIn('SWITCH_AT_MS',text)


if __name__=='__main__':unittest.main()
