import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from assemble_edit import assemble, run, audio_hash


class AssemblyTest(unittest.TestCase):
    def test_complete_audio_bounded_restore_and_underflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, edit = root / 'source.mp4', root / 'edit.mp4'
            run('ffmpeg', ['-v','error','-f','lavfi','-i','color=red:s=64x64:r=30:d=1',
                           '-f','lavfi','-i','sine=frequency=440:duration=1.12','-c:v','libx264','-c:a','aac',source])
            run('ffmpeg', ['-v','error','-f','lavfi','-i','color=blue:s=64x64:r=30:d=1','-c:v','libx264',edit])
            spec = {'version':1,'source':'source.mp4','fps':'30/1','frames':30,
                    'segments':[{'path':'edit.mp4','start_frame':0,'frames':30,'timeline_start':0}],
                    'restore_regions':[{'x':32,'y':32,'width':32,'height':32,'start_frame':3,'end_frame':12},{'x':0,'y':0,'width':32,'height':32,'start_frame':0,'end_frame':15}]}
            manifest = root / 'edit.json'; manifest.write_text(json.dumps(spec))
            output = root / 'result.mp4'; report = assemble(manifest, output)
            self.assertEqual(audio_hash(source), audio_hash(output))
            self.assertEqual(report['output']['frames'], 30)
            self.assertEqual(report['human_approval'], 'pending')
            # Actual decoded pixels: original inset before boundary, generated blue after.
            import subprocess
            from media_runtime import executable
            pixels = subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(output),
                '-vf','crop=2:2:8:8','-pix_fmt','rgb24','-f','rawvideo','-'])
            self.assertGreater(pixels[14*12], pixels[14*12+2])
            self.assertGreater(pixels[15*12+2], pixels[15*12])
            with self.assertRaisesRegex(ValueError, 'already exists'):
                assemble(manifest, output)
            spec['restore_regions'][0]['end_frame'] = 31
            manifest.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, 'Restore region'):
                assemble(manifest, root/'outside.mp4')
            spec['restore_regions'][0]['end_frame'] = 12
            # Provider FPS drift must be explicitly accepted, not silently converted.
            run('ffmpeg', ['-v','error','-f','lavfi','-i','color=blue:s=64x64:r=24:d=1','-c:v','libx264',root/'24.mp4'])
            spec['segments'][0]['path'] = '24.mp4'
            manifest.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, 'allow_fps_conform'):
                assemble(manifest, root/'fps.mp4')
            spec['allow_fps_conform'] = True
            manifest.write_text(json.dumps(spec))
            self.assertTrue(assemble(manifest, root/'conformed.mp4')['fps_conformed'])
            spec['segments'][0]['path'] = 'edit.mp4'
            spec['segments'][0]['start_frame'] = 1
            manifest.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, 'underflow'):
                assemble(manifest, root/'short.mp4')
            self.assertFalse((root/'short.mp4').exists())
            spec['segments'][0]['timeline_start'] = 1
            manifest.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, 'gaps or overlaps'):
                assemble(manifest, root/'gap.mp4')


if __name__ == '__main__':
    unittest.main()
