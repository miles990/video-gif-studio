"""Static SVG safety CLI."""
import sys
from imagegen import main
if __name__=='__main__':raise SystemExit(main(['svg-safe',*sys.argv[1:]]))
