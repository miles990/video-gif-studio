from image_fixtures import ImageCase
from image_route import Adapter
from image_common import ImageError
from datetime import datetime,timezone,timedelta
class PriceGuardTests(ImageCase):
 def adapter_for(self,unit=.1,when=None):
  return Adapter(self.path/'api',price_table_trusted=True,prices=dict(version='offline-test',date=when or datetime.now(timezone.utc).date().isoformat(),rows=[dict(model='gpt-image-2.6-flare',quality='low',size='1024x1024',unit_usd=unit)]))
 def test_zero_stale_future_and_rounded_zero_refused(self):
  for unit,when in [(0,None),(1e-12,None),(.1,'2000-01-01'),(.1,(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()),(.1,'invalid')]:
   with self.subTest(unit=unit,date=when):
    with self.assertRaises(ImageError) as cm:self.adapter_for(unit,when).estimate(self.request(route='api'))
    self.assertEqual(cm.exception.error['code'],'E_PRICE_REQUIRED')
 def test_default_zero_budget_cannot_dispatch(self):
  adapter=self.adapter_for();req=self.request(route='api');estimate=adapter.estimate(req)
  with self.assertRaises(ImageError) as cm:adapter.approve(req,estimate['estimate_id'],0)
  self.assertEqual(cm.exception.error['code'],'E_BUDGET');self.assertEqual(adapter.records(),[])
 def test_even_forged_zero_estimate_cannot_bypass_budget(self):
  from unittest.mock import patch
  adapter=self.adapter_for()
  with patch.object(adapter,'estimate',return_value=dict(estimate_id='zero',cost_estimate_usd=0)):
   with self.assertRaises(ImageError):adapter.approve(self.request(route='api'),'zero',0)
