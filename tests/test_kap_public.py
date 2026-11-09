"""The KAP public feed is always explicitly unverified for payment information."""
import json
import sys
import unittest
from pathlib import Path

class TestKapPublic(unittest.TestCase):
    def test_public_reference_status_if_present(self):
        root=Path(__file__).resolve().parent.parent
        path=root/'public'/'data'/'kap_watch.json'
        if not path.exists():
            self.skipTest('No successful KAP publication exists yet')
        doc=json.loads(path.read_text('utf8'))
        self.assertFalse(doc['payment_data_verified'])
        self.assertFalse(doc['holdings_are_live_trades'])
        self.assertEqual(doc['status'],'PILOT_VERIFIED')
        self.assertTrue(doc['retrieved_at'])
        sys.path.insert(0,str(root/'scripts'))
        from kap_watch import CODES
        self.assertGreaterEqual(len(doc['funds']),2)
        self.assertTrue({'TLY','TP2'}.issubset({f['code'] for f in doc['funds']}))
        self.assertTrue({f['code'] for f in doc['funds']}.issubset(set(CODES)))
        self.assertTrue(all(f['payment_status']=='NOT_VERIFIED' for f in doc['funds']))
if __name__=='__main__':unittest.main()
