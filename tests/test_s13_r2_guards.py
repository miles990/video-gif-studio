import json,subprocess,sys
from datetime import datetime,timezone
from unittest.mock import patch
from image_fixtures import ImageCase,ROOT
from image_route import Adapter
from image_common import ImageError,read,write
from image_keyframes import keyframes
from test_image_keyframes import board

class GuardsRound2(ImageCase):
 def test_generation_retry_failure_keeps_first(self):
  original=self.adapter.generate
  def generate(req,out,*args,**kw):
   if 'identity-retry' in str(out):raise ImageError('E_GENERATION','retry unavailable')
   return original(req,out,*args,**kw)
  b=board();b['shots']=b['shots'][:1]
  self.configure(image=str(self.fixture))  # exact 9:16; no aspect failure before QA
  with patch.object(self.adapter,'generate',side_effect=generate) as dispatch,patch('image_identity.check',return_value=dict(status='identity_fail')) as identity:
   result=keyframes(b,self.adapter,self.path/'kf',self.request(refset_path='fake'))
  self.assertEqual(dispatch.call_count,2);self.assertIn('identity-retry',str(dispatch.call_args_list[1].args[1]));identity.assert_called_once()
  self.assertIn('keyframe',result['shots'][0])
  qa=read(result['shots'][0]['keyframe']['gen_manifest'])['qa']['identity']
  self.assertEqual(qa['retry_error']['code'],'E_GENERATION');self.assertEqual(qa['generation_retained'],'first')

 def test_all_failed_cli_and_alternatives(self):
  b=board();b['shots']=b['shots'][:1];write(self.path/'board.json',b);self.configure(error='unavailable')
  result=subprocess.run([sys.executable,str(ROOT/'scripts/imagegen.py'),'keyframes',str(self.path/'board.json'),'--experimental','--out',str(self.path/'kf'),'--state',str(self.path/'state'),'--codex',str(self.fake)],capture_output=True,text=True)
  self.assertNotIn('retained',json.loads(result.stdout)['error']['message'])
  self.configure(login='Not logged in')
  with self.assertRaises(ImageError) as cm:self.adapter.login()
  alternatives=' '.join(cm.exception.error['alternatives']).lower()
  self.assertIn('grok',alternatives);self.assertIn('silhouette',alternatives)

 def table(self):
  p=self.path/'prices.json';write(p,dict(version='forged-current',date=datetime.now(timezone.utc).date().isoformat(),rows=[dict(model='gpt-image-2.6-flare',quality='low',size='1024x1024',unit_usd=1e-8)]));return p

 def test_forged_current_price_rejected_even_with_budget(self):
  adapter=Adapter(self.path/'api',prices=self.table())
  with patch.object(adapter,'api_images') as dispatch:
   with self.assertRaises(ImageError) as cm:adapter.generate(self.request(route='api'),self.path/'paid','forged-estimate',1)
   self.assertEqual(cm.exception.error['code'],'E_PRICE_UNTRUSTED');dispatch.assert_not_called()
 def test_explicit_trust_is_bound_to_estimate(self):
  from image_common import digest
  p=self.table();adapter=Adapter(self.path/'api',prices=p,price_table_trusted=True)
  estimate=adapter.estimate(self.request(route='api'))
  self.assertTrue(estimate['price_table_trusted']);self.assertEqual(estimate['price_table_sha256'],digest(p))
  with self.assertRaises(ImageError):adapter.approve(self.request(route='api'),estimate['estimate_id'],0)
