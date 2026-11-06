import sys,unittest,tempfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_preview import decode_preview
from image_common import ImageError
from media_runtime import executable
FIX=Path(__file__).parent/'fixtures/live-s15/explore.wav'


class PreviewDecodeTest(unittest.TestCase):
    def test_local_hls_aac_transport_stream_and_fragmented_mp4(self):
        for kind in ('mpegts','fmp4'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
                folder=Path(folder);playlist=folder/'local.m3u8'
                subprocess.run([executable('ffmpeg'),'-v','error','-y','-i',str(FIX.resolve()),
                                '-c:a','aac','-b:a','128k','-f','hls','-hls_time','1','-hls_list_size','0',
                                '-hls_segment_type',kind,str(playlist)],capture_output=True,check=True,cwd=folder)
                pcm,r=decode_preview(playlist,folder/'analysis',max_seconds=4)
                self.assertEqual(r['codec'],'aac');self.assertEqual(r['container'],'hls')
                self.assertTrue(r['preview_only']);self.assertGreater(len(pcm),48000*3)
                self.assertLessEqual(len(pcm),48000*4)
                self.assertNotIn('http',r['protocol_whitelist'])

    def test_opus_and_unknown_provider_encoding(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);opus=folder/'preview.opus'
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-i',str(FIX),'-c:a','libopus',str(opus)],capture_output=True,check=True)
            _,r=decode_preview(opus,folder/'analysis')
            self.assertEqual(r['codec'],'opus')
            bad=folder/'payload.bin';bad.write_bytes(b'1.0.0 unknown proprietary transport')
            with self.assertRaises(ImageError) as error:decode_preview(bad,folder/'analysis',encoding='1.0.0')
            self.assertEqual(error.exception.error['code'],'E_PREVIEW_ENCODING')
            with self.assertRaises(ImageError):decode_preview(opus,folder/'delivery')


if __name__=='__main__':unittest.main()
