"""Run final evidence serially with the supplied interpreter/runtime."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]


def call(args,log,check=True):
    with (ROOT/'wow/fx'/log).open('w',encoding='utf-8') as stream:
        code=subprocess.call([sys.executable,'-B',*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    print(log+': exit '+str(code),flush=True)
    if check and code:raise RuntimeError('See '+log)
    return code


def main():
    call(['scripts/fx_calibrate.py'],'test-s6-cost.log')
    call(['wow/fx/verify_s6_integration.py'],'test-s6-integration.log')
    code=call(['-m','unittest','discover','-s','tests'],'test-s6-final.log',False)
    print('Full suite result must be compared with the recorded 561 / two-environment-error baseline.',flush=True)
    return code


if __name__=='__main__':raise SystemExit(main())
