"""Schema and safety checks for the KAP reference-only pilot."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
from kap_watch import watch_record

class TestKapWatch(unittest.TestCase):
    def payloads(self,code='TLY'):
        p={'code':code,'holdings':{'code':code,'latestPeriod':'2026-10',
                'latestPublishDate':1793500000000,'items':[{'asset_name':'Test','weight':4.1}]}}
        d={'code':code,'disclosures':{'code':code,'items':[
                {'disclosure_index':1690001,'publish_date':1793500000000,
                 'subject':'Katılma payı iade ödemeleri'},
                {'disclosure_index':1690001,'publish_date':1793500000000,
                 'subject':'Duplicate'},
                {'disclosure_index':'bad','publish_date':1793500000000,'subject':'Invalid'}
        ]}}
        return p,d
    def test_status_never_paid(self):
        p,d=self.payloads()
        rec=watch_record('TLY',p,d)
        self.assertEqual(rec['payment_status'],'NOT_VERIFIED')
        self.assertFalse(rec['holdings_used_in_original_dashboard'])
        self.assertEqual(rec['holdings_record_count'],1)
        self.assertEqual(len(rec['latest_disclosures']),1)
        self.assertTrue(rec['latest_disclosures'][0]['kap_url'].endswith('/1690001'))
    def test_fund_identity_required(self):
        p,d=self.payloads()
        with self.assertRaises(ValueError):
            watch_record('TP2',p,d)
    def test_invalid_kap_block_rejected(self):
        p,d=self.payloads()
        p['holdings']['items']=[]
        with self.assertRaises(ValueError):
            watch_record('TLY',p,d)
    def test_unsafe_or_invalid_index_ignored(self):
        p,d=self.payloads()
        d['disclosures']['items'].append({'disclosure_index':0,
            'publish_date':1793500000000,'subject':'No'})
        rec=watch_record('TLY',p,d)
        self.assertEqual(len(rec['latest_disclosures']),1)
if __name__=='__main__':unittest.main()
