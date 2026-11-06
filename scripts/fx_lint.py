"""Lint conflicts, flash cadence and energy-dependent effect budgets."""
import argparse
import json
from pathlib import Path
import sys
from fx_director import lint
from fx_calibrate import load_table


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path)
    ap.add_argument('--calibration',type=Path);ap.add_argument('--out',type=Path)
    ap.add_argument('--tokens',type=Path);ap.add_argument('--storyboard',type=Path)
    ap.add_argument('--taste-report',type=Path)
    ap.add_argument('--movie',type=Path,help='Decoded movie for storyboard subject_mask focal checks')
    a=ap.parse_args(argv)
    try:
        plan=json.loads(a.plan.read_text(encoding='utf-8-sig'))
        beats=json.loads((a.plan.parent/plan['beatmap']).read_text(encoding='utf-8')) if 'beatmap' in plan else {}
        plan.setdefault('sections',beats.get('sections',[]));plan.setdefault('downbeats_ms',beats.get('downbeats_ms',[]))
        if plan.get('segments'):
            from fx_render import validate_plan
            # Use the renderer's trim/loop/beat resolver, not guessed durations.
            validated=validate_plan(a.plan,('mp4',),experimental=True,_silent_derivative=True)
            resolved,ctx=validated[2:4]
            plan['fps']=ctx.fps;plan['downbeats_ms']=ctx.downbeats_ms
            beats['beats_ms']=ctx.beats_ms
            plan['segments']=[dict(original,start_ms=s['start_ms'],duration_ms=s['duration_ms']) for original,s in zip(plan['segments'],resolved)]
        report=lint(plan,beats.get('beats_ms'),load_table(a.calibration))
        if a.tokens or a.storyboard or a.taste_report:
            from taste_common import read
            from taste_lint import token_lint, intent_lint, edit_lint, weakest, exemption_summary
            board=read(a.storyboard) if a.storyboard else {}
            findings=token_lint(plan,read(a.tokens)) if a.tokens else []
            if board:findings+=intent_lint(board)
            if board and a.movie:
                from mastery_lint import focal_movie
                report['focal']=focal_movie(a.movie,board,a.storyboard.parent)
                findings+=report['focal']['findings']
            if a.taste_report:
                measured=read(a.taste_report);findings+=edit_lint(measured,board)
                report['weakest']=weakest(measured)
            report['taste_findings']=findings
            report['taste_exemptions']=exemption_summary(board or plan,findings)
        text=json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)
        if a.out:a.out.write_text(text+'\n',encoding='utf-8')
        print(text);return int(report['errors']>0)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        print('fx_lint: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
