"""Fresh-cache, different-hash-seed calibration and automatic plugin evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]


def main():
    root=Path(tempfile.mkdtemp(prefix='vgs-s6-calibration-'))
    tables=[]
    for seed in ('0','123'):
        path=root/(seed+'.json')
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/fx_calibrate.py'),'--out',str(path),'--force','--no-costs'],
                       cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED=seed),check=True)
        tables.append(json.loads(path.read_text()))
    differences={}
    for name,a in tables[0]['effects'].items():
        b=tables[1]['effects'][name]
        differences[name]=max(abs(x['perceived']-y['perceived']) for x,y in zip(a['rows'],b['rows']))
        if differences[name]>.01:raise AssertionError('Calibration drift: '+name)
    plugins=root/'plugins';plugins.mkdir()
    (plugins/'dim.py').write_text("from fx.core import effect\n@effect(card={'intent':['breathe'],'needs':[],'energy':.2})\ndef s6_dim(frame,t,ctx,amount=1.):\n frame[...,:3]*=1-.5*amount\n return frame\n")
    path=root/'plugin.json'
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/fx_calibrate.py'),'--fx-dir',str(plugins),'--effect','s6_dim','--out',str(path),'--no-costs'],cwd=ROOT,check=True)
    plugin=json.loads(path.read_text())['effects']['s6_dim']
    if not plugin['monotonic'] or plugin['rows'][0]['perceived']>.02:raise AssertionError('Invalid automatic plugin calibration')
    report=dict(hash_seeds=[0,123],fresh_caches=True,per_effect_max_absolute_difference=differences,
                plugin=dict(name='s6_dim',monotonic=plugin['monotonic'],max_perceived=plugin['max_perceived'],rows=len(plugin['rows'])),artifacts=str(root))
    (ROOT/'wow/fx/s6-calibration-repro.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
