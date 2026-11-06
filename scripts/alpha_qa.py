"""Standalone transparent-image QA entry point (maps to vgs image alpha)."""
import sys
from imagegen import main
if __name__=='__main__':raise SystemExit(main(['alpha',*sys.argv[1:]]))
