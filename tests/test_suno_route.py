"""Offline fake transport; no provider SDK or network is used."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import tempfile
import unittest
from suno_route import Ledger,Session,cache_key,plan
from image_common import ImageError
from suno_fake import FakeSuno,SCHEMAS


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.fake=FakeSuno();self.ledger=Ledger(Path(self.tmp.name)/'ledger.json');self.session=Session(self.ledger,self.fake,sleep=lambda x:None)
    def test_cache_normalization_and_schema(self):
        self.assertEqual(cache_key('x',{'tempo':120.0,'s':'  Ａ '}),cache_key('x',{'s':'A','tempo':120}))
        p=plan(dict(kind='score',duration=30,bpm=120,key='Am'))
        self.assertNotIn('tempo',p['params']);self.assertNotIn('key',p['params'])
        q=dict(kind='bgm-loop',bpm=120,key='Am')
        self.session.create(q,True);self.session.create(q,True)
        self.assertEqual(self.ledger.usage()['create_calls'],1);self.assertEqual(self.ledger.usage()['song_credits'],2)
    def test_cap_cache_and_unselected(self):
        with self.assertRaises(ImageError):self.session.download('x')
        for i in range(5):self.ledger.select(str(i),'standing:test');self.session.download(str(i))
        before=len(self.fake.calls);self.session.download('0');self.assertEqual(len(self.fake.calls),before)
        self.ledger.select('six','user')
        with self.assertRaises(ImageError):self.session.download('six')
        self.assertEqual(sum(p.get('confirm',False) for t,p in self.fake.calls if t=='audio_download'),5)
    def test_boundary_and_runtime_guard(self):
        for balance in (67,12,10):
            self.fake.balance=balance;clip=str(balance);self.ledger.select(clip,'user');self.session.download(clip)
        self.fake.balance=9;self.ledger.select('nine','user')
        with self.assertRaises(ImageError):self.session.download('nine')
        other=Ledger(Path(self.tmp.name)/'other.json')
        with self.assertRaises(ImageError):other.guard('audio_download',dict(id='unauthorized',confirm=True),dict(download_credits_remaining=67))
    def test_free_download_and_retry(self):
        self.ledger.select('free','user');self.fake.script=[dict(url='https://invalid.test/free')]
        self.session.download('free');self.assertEqual(self.ledger.usage()['download_credits'],0)
        self.ledger.select('retry','user');self.fake.script=[dict(reason='rate_limited'),dict(status='processing'),dict(url='https://invalid.test/retry')]
        waits=[];self.session.sleep=waits.append;self.session.download('retry');self.assertEqual(waits,[1,1])
    def test_daily_stops_queue(self):
        self.ledger.select('stop','user');self.fake.script=[dict(reason='daily_limit_exceeded')]
        with self.assertRaises(ImageError):self.session.download('stop')
        self.assertTrue(self.ledger.data['halted'])
    def test_fake_all_schemas_and_idempotency_conflict(self):
        self.assertEqual(len(SCHEMAS),35)
        p=dict(description='offline',tempo=120,loop=True,idempotency_key='fixed')
        a=self.fake('sounds_create',p);b=self.fake('sounds_create',p)
        self.assertEqual(a['clip_ids'],b['clip_ids']);self.assertTrue(b['Idempotency-Replayed'])
        self.assertEqual(self.fake('sounds_create',dict(p,tempo=123))['code'],409)
        self.assertEqual(self.fake('audio_create',dict(tempo=120))['code'],400)
        self.assertEqual(self.fake('sounds_create',dict(description='x',duration=8))['code'],400)
    def test_poll_terminal_and_listen_concurrency(self):
        self.fake.queue('audio_analysis',dict(status='processing'),dict(status='unavailable'))
        self.assertEqual(self.session.poll('audio_analysis',dict(id='fake'))['status'],'unavailable')
        for _ in range(5):self.session.call('audio_listen',dict(id='fake',question='offline'))
        count=len(self.fake.calls)
        with self.assertRaises(ImageError):self.session.call('audio_listen',dict(id='fake',question='sixth'))
        self.assertEqual(len(self.fake.calls),count)
        self.session.poll('audio_listen_wait',dict(id='listen-0'))
        self.session.call('audio_listen',dict(id='fake',question='replacement'))
    def test_delayed_download_settlement_still_reserves_cap(self):
        for i in range(5):
            clip='delayed-'+str(i);self.ledger.select(clip,'user')
            self.fake.script=[dict(status='requires_credit'),dict(url='https://invalid.test/'+clip)]
            self.session.download(clip)
        self.assertEqual(self.ledger.usage()['download_credits'],0) # Not observed yet.
        self.ledger.select('sixth','user')
        with self.assertRaises(ImageError):self.session.download('sixth')
        self.assertEqual(self.fake.confirm_calls,5)


if __name__=='__main__':unittest.main()
