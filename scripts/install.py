#!/usr/bin/env python3
"""Install from a trusted checkout without replacing an existing skill."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

NAME = 'video-gif-studio'


def install(source, skills_dir, skip_deps=False, with_matting=False):
    source = Path(source).resolve()
    if not (source/'SKILL.md').is_file() or not (source/'requirements.txt').is_file():
        raise ValueError('Source is not a complete video-gif-studio checkout')
    target = Path(skills_dir).expanduser()/NAME
    if target.exists() or target.is_symlink():
        if target.resolve() != source:
            raise ValueError(f'既有安裝已保留：{target} 不是這個來源，因此沒有覆寫任何檔案。若要修復該安裝，請在該目錄執行它自己的 install.py；若要裝到別處，請改用 --skills-dir <新目錄>。')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        # A staging sibling prevents an interrupted copy appearing installed.
        import tempfile
        stage = Path(tempfile.mkdtemp(prefix='.video-gif-install-', dir=target.parent))
        try:
            shutil.copytree(source,stage,dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('.git','.venv','.runtime','__pycache__','*.pyc','output','run-*','local-settings.json','.env*'))
            stage.rename(target)
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            raise
    runtime = target/'.venv'
    python = runtime/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not skip_deps:
        if sys.version_info < (3,11):
            raise ValueError('Run installer with Python 3.11 or newer')
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(runtime)
        subprocess.run([str(python),'-m','pip','install','-r',str(target/'requirements.txt')],check=True)
        if with_matting:
            subprocess.run([str(python),'-m','pip','install','-r',str(target/'requirements-matting.txt')],check=True)
        subprocess.run([str(python),str(target/'scripts/media_runtime.py'),'--install'],check=True)
        for script in ('gif_pipeline.py','vgs.py','grok_video.py'):
            subprocess.run([str(python),str(target/'scripts'/script),'--help'],check=True,stdout=subprocess.DEVNULL)
    result = {'skill':str(target),'skill_registered':(target/'SKILL.md').is_file(),
              'python':str(python),'dependencies':'not checked (--skip-deps)' if skip_deps else 'ready',
              'note':'Grok generation entitlement and credits are not verified by installation'}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--skills-dir',type=Path,help='Override all target selection')
    ap.add_argument('--target',choices=['claude','codex'],help='Default: CODEX_HOME, existing ~/.codex, existing ~/.claude, otherwise ~/.codex')
    ap.add_argument('--skip-deps',action='store_true',help='Registration-only test; does not claim runtime readiness')
    ap.add_argument('--with-matting',action='store_true',help='Install optional CPU foreground separation backend')
    args=ap.parse_args()
    try:
        home=Path.home()
        if args.skills_dir: dest=args.skills_dir
        elif args.target == 'claude': dest=home/'.claude'/'skills'
        elif args.target == 'codex': dest=Path(os.environ.get('CODEX_HOME',str(home/'.codex')))/'skills'
        elif os.environ.get('CODEX_HOME'): dest=Path(os.environ['CODEX_HOME'])/'skills'
        elif (home/'.codex').exists(): dest=home/'.codex'/'skills'
        elif (home/'.claude').exists(): dest=home/'.claude'/'skills'
        else: dest=home/'.codex'/'skills'
        result=install(args.source,dest,args.skip_deps,args.with_matting)
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
