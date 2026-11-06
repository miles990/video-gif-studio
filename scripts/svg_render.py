"""Render traced static SVG at selected short-edge sizes."""
import sys
from imagegen import main
if __name__=='__main__':raise SystemExit(main(['svg-render',*sys.argv[1:]]))
