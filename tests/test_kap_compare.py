"""Safe KAP cross-source comparisons; no inferred trades or payment decisions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
from kap_compare import compare_portfolios, fingerprint
from kap_watch import watch_record

class TestKapComparison(unittest.TestCase):
    def test_unique_code_delta(self):
        original=[['ABC','F','DSTKF','',None,'Hisse',25.32],
                  ['ABC','F','OZATD','',None,'Hisse',20.22],
                  ['ABC','F','BPP','',None,'Nakit',15.0]]
        latest=[{'asset_code':'DSTKF','asset_type':'stock','weight':24.9},
                {'asset_code':'OZATD','asset_type':'stock','weight':20.22},
                {'asset_code':'BPP','asset_type':'cash','weight':15.0}]
        result=compare_portfolios(original,'ABC',latest,'2026-09')
        self.assertFalse(result['periods_confirmed_equal'])
        self.assertEqual(result['comparable_unique_codes'],2)
        self.assertEqual(result['top_weight_differences'][0]['asset_code'],'DSTKF')
        self.assertAlmostEqual(result['top_weight_differences'][0]['difference_percentage_points'],-.42)
        self.assertEqual(result['original_portfolio_period'],'UNKNOWN')
    def test_duplicate_codes_are_not_compared(self):
        original=[['ABC','F','DSTKF','',None,'Hisse',6.0],
                  ['ABC','F','DSTKF','',None,'Ters Repo',-2.0]]
        new=[{'asset_code':'DSTKF','weight':4.0}]
        result=compare_portfolios(original,'ABC',new,'2026-09')
        self.assertEqual(result['comparable_unique_codes'],0)
        self.assertEqual(result['ambiguous_duplicate_codes'],['DSTKF'])
        self.assertEqual(result['status'],'INSUFFICIENT_COMPARABLE_CODES')
    def test_fingerprint_order_independent(self):
        a=[{'asset_code':'AAPL','asset_type':'stock','weight':1.2},
           {'asset_code':'VAKBN','asset_type':'stock','weight':3.1}]
        self.assertEqual(fingerprint(a),fingerprint(list(reversed(a))))
        b=[dict(a[0],weight=1.3),a[1]]
        self.assertNotEqual(fingerprint(a),fingerprint(b))
    def test_review_flag_is_not_payment_confirmation(self):
        p={'code':'TLY','holdings':{'code':'TLY','latestPeriod':'2026-09','items':[{'asset_code':'DSTKF','weight':25.0}]}}
        d={'code':'TLY','disclosures':{'code':'TLY','items':[
            {'disclosure_index':1664916,'subject':'Genel Açıklama','summary':'Katılma Payı İade Ödemeleri Hk.','publish_date':1789661985000}
        ]}}
        result=watch_record('TLY',p,d)
        self.assertEqual(result['payment_status'],'NOT_VERIFIED')
        self.assertEqual(result['payment_review_candidates'],[1664916])
        self.assertTrue(result['latest_disclosures'][0]['payment_review_candidate'])

if __name__=='__main__':unittest.main()
