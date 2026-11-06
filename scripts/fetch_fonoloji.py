"""Fonoloji CSV toplu servisi, kaynak kolonları doğrulanmadan veri yayını yapmaz."""
import csv
import io
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

URL = "https://fonoloji.com/v1/funds.csv"

def norm_key(value):
    value=str(value or "").strip().replace("İ","I").replace("ı","i")
    value="".join(x for x in unicodedata.normalize("NFKD",value) if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]+","_",value.lower()).strip("_")

ALIASES={
    "code":["code","kod","fon_kodu","fund_code","fundcode","tefas_code"],
    "current_date":["current_date","price_date","date","tarih","fiyat_tarihi","last_seen"],
    "current_price":["current_price","price","nav","birim_fiyat","fiyat","pay_fiyati"],
    "aum":["aum","total_value","fon_buyuklugu","fon_toplam_degeri","total_assets","fund_size"],
    "investor_count":["investor_count","investors","yatirimci_sayisi","yatirimci_adedi","number_of_investors"]
}
def parse_csv(body):
    value=body.decode("utf-8-sig")
    if value.lstrip().startswith("<"):
        raise ValueError("Servis CSV yerine HTML döndürdü")
    dialect=csv.Sniffer().sniff(value[:4096],delimiters=",;\t")
    reader=csv.DictReader(io.StringIO(value),dialect=dialect)
    found={norm_key(x):x for x in reader.fieldnames or []}
    cols={}
    for key,options in ALIASES.items():
        src=next((found[c] for c in options if c in found),None)
        if src is None: raise ValueError(f"CSV alanı eksik: {key}; kolonlar={list(found)}")
        cols[key]=src
    rows=[]
    for row in reader:
        rec={field:str(row.get(col) or "").strip() for field,col in cols.items()}
        if rec["code"]: rows.append(rec)
    if len(rows)<100:
        raise ValueError(f"Toplu CSV anormal küçük ({len(rows)})")
    return rows

def fetch():
    key=os.environ.get("FONOLOJI_KEY","")
    if len(key)<8:raise ValueError("GitHub Actions Secret FONOLOJI_KEY girilmedi")
    req=urllib.request.Request(URL,headers={"X-API-Key":key,"User-Agent":"FonTakipDashboard/1.0","Accept":"text/csv"})
    err=None
    for n in range(3):
        try:
            with urllib.request.urlopen(req,timeout=35) as response:
                if response.status!=200: raise RuntimeError(f"HTTP {response.status}")
                body=response.read(10_000_001)
                if len(body)>10_000_000: raise ValueError("CSV çok büyük")
                return parse_csv(body)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError) as exc:
            err=exc
            if isinstance(exc,urllib.error.HTTPError) and exc.code in (400,401,403,404,429):
                break
            if n<2:time.sleep(2*(n+1))
    raise RuntimeError(f"Fonoloji verisi alınamadı: {err}")
