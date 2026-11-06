import datetime as dt
import hashlib
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"scripts"))

from bootstrap import build, EXPECTED, SIZE
from fon_core import block, apply_updates
from fetch_fonoloji import parse_csv

class TestProtectedSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=build()
        cls.html=raw.decode("utf8")
        cls.fl=block(cls.html,"FL")[0]

    def test_source_unchanged(self):
        source=Path(__file__).resolve().parent.parent/"source"/"index.html"
        raw=source.read_bytes()
        self.assertEqual(len(raw),SIZE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),EXPECTED)

    def test_expected_fund_scope(self):
        self.assertGreaterEqual(len(self.fl["funds"]),2000)
        self.assertGreaterEqual(len(self.fl["rows"]),10000)
        self.assertEqual(len({x[0] for x in self.fl["funds"]}),len(self.fl["funds"]))

    def test_all_nonprice_blocks_present(self):
        for key in ("R","AYAR","KAL","RA","RAFD","LOGOS"):
            self.assertIsNotNone(block(self.html,key)[0])

    def test_csv_parse(self):
        text="code,current_date,current_price,aum,investor_count\n"
        text+="".join(f"T{i:03d},2026-11-06,12.345,10000,20\n" for i in range(150))
        rows=parse_csv(text.encode("utf8"))
        self.assertEqual(len(rows),150)
        self.assertEqual(rows[0]["current_price"],"12.345")

    def test_sparse_response_not_published(self):
        code=self.fl["funds"][0][0]
        rows=[{"code":code,"current_date":"2026-11-06","current_price":1,
               "aum":100,"investor_count":1}]
        _,_,r=apply_updates(self.html,{},rows,today=dt.date(2026,11,6))
        self.assertFalse(r["publish"])

    def test_complete_update_preserves_nonprice_data(self):
        rows=[]
        for f in self.fl["funds"]:
            if f[6] and f[6]>0:
                rows.append({"code":f[0],"current_date":"2026-11-06",
                             "current_price":1.1,"aum":f[6]*1.01,
                             "investor_count":f[5] if f[5] is not None else 0})
        updated,state,r=apply_updates(self.html,{},rows,today=dt.date(2026,11,6))
        self.assertTrue(r["publish"],r)
        for key in ("R","KAL","RA","RAFD","LOGOS"):
            self.assertEqual(block(updated,key)[0],block(self.html,key)[0])
        self.assertEqual(len(block(updated,"FL")[0]["rows"]),len(self.fl["rows"]))
        self.assertGreater(len(state),2000)

if __name__=="__main__":unittest.main()
