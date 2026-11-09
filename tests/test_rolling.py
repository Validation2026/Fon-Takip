import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
from bootstrap import build
from fon_core import block
from update_rolling import budget,normalize_fund,validate,refreshed_html

class RollingRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=build().decode('utf8')
        cls.fl,_,_=block(cls.base,'FL')
    def test_budget(self):
        self.assertEqual(budget({'today':3000,'this_month':30000}),400)
        self.assertEqual(budget({'today':200,'this_month':30000}),170)
        self.assertEqual(budget({'today':3000,'this_month':115}),15)
        with self.assertRaises(ValueError):budget({'today':'3000','this_month':30000})
    def test_provider_identity(self):
        r=normalize_fund({'fund':{'code':'AAJ','current_date':'2026-11-09','current_price':1.2,'aum':50000,'investor_count':10}},'AAJ')
        self.assertEqual(r['investor_count'],10)
        with self.assertRaises(ValueError):normalize_fund({'fund':{'code':'BAD'}},'AAJ')
    def test_validation(self):
        f=self.fl['funds'][0]
        good={'code':f[0],'current_date':'2026-11-09','current_price':1.2,'aum':f[6]*1.01,'investor_count':123}
        value,error=validate(good,{},f[6],dt.date(2026,11,9))
        self.assertEqual(error,None)
        self.assertEqual(value['aum'],good['aum'])
        _,error=validate(dict(good,current_date='2026-12-09'),{},f[6],dt.date(2026,11,9))
        self.assertEqual(error,'invalid_date')
    def test_html_integrity(self):
        f=self.fl['funds'][0]
        update={f[0]:{'current_date':'2026-11-09','current_price':1.0,'aum':f[6]*1.01,'investor_count':int(f[5])}}
        result=refreshed_html(self.base,update)
        newer,_,_=block(result,'FL')
        self.assertEqual(len(newer['funds']),len(self.fl['funds']))
        self.assertEqual(len(newer['rows']),len(self.fl['rows']))
        for name in ('R','KAL','RA','RAFD','LOGOS'):
            self.assertEqual(block(result,name)[0],block(self.base,name)[0])
        self.assertEqual(block(result,'AYAR')[0]['vgun'],'Fon bazında farklı')

if __name__=='__main__':unittest.main()
