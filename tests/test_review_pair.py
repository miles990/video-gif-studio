import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from review_pair import build
class ReviewPairTests(unittest.TestCase):
    def test_rejects_unbounded_requests_before_reading_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            for values in ({'samples':1000},{'offset':float('nan')},{'offset':float('inf')}):
                with self.assertRaises(ValueError):build('missing-a','missing-b',Path(tmp)/'new',**values)
    def test_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'keep.txt';marker.write_text('keep')
            with self.assertRaises(ValueError):build('missing-a','missing-b',tmp)
            self.assertEqual(marker.read_text(),'keep')
