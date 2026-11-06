from pathlib import Path
from image_fixtures import ImageCase,intended_gaps
from image_alpha import alpha_qa
from s13_r4_judge_replay import replay
import test_s13_r4_alpha


class JudgeReplayRound4(ImageCase):
 def test_saved_inputs_replay_and_disagreement_fail_closed(self):
  result=alpha_qa(test_s13_r4_alpha.AlphaRound4.art(self),judge=intended_gaps,overlay_path=self.path/'full.png')
  case=dict(name='known',inputs=result['hole_review']['inputs'],regions=2,injected_region_ids=[1],other_issues=[])
  def judge(path,regions):
   return {'regions':[dict(id=r['id'],classification='body_hole' if r['label']==1 else 'intended_gap',reason='known mask') for r in regions]}
  live=replay(case,judge)
  self.assertEqual(live['status'],'FAIL');self.assertTrue(live['detected']);self.assertEqual(live['designed_false_alarm'],0)
  seen=[]
  def disagree(path,regions):
   seen.append(path)
   return judge(path,regions) if len(seen)==1 else intended_gaps(path,regions)
  live=replay(case,disagree)
  self.assertEqual(live['status'],'needs_review');self.assertFalse(live['detected'])
