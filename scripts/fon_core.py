"""Korunmuş HTML verilerini kontrollü güncelleyen standart-kütüphane modülü."""
import copy
import datetime as dt
import hashlib
import json
import math
import re
from collections import Counter, defaultdict

BASE_DATE = dt.date(2026, 11, 5)
MONTHS = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
BLOCKS = ("R", "FL", "AYAR", "KAL", "RA", "RAFD", "LOGOS")

def block(html, name):
    m = re.search(r"(?m)^const\s+" + re.escape(name) + r"\s*=\s*", html)
    if not m:
        raise ValueError("Kaynak veride nesne bulunamadı: " + name)
    obj, size = json.JSONDecoder().raw_decode(html[m.end():])
    return obj, m.end(), m.end()+size

def patch(html, name, obj):
    _, start, end = block(html, name)
    value = json.dumps(obj, ensure_ascii=False, separators=(",",":"), allow_nan=False).replace("</","<\\/")
    return html[:start]+value+html[end:]

def numeric(x):
    if x is None or x == "" or isinstance(x,bool): return None
    try:
        if isinstance(x,str):
            x = x.strip().replace("₺","").replace(" ","")
            if "," in x and "." in x:
                x = x.replace(".","").replace(",",".") if x.rfind(",")>x.rfind(".") else x.replace(",","")
            elif "," in x: x = x.replace(",",".")
        v = float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):
        return None

def day(x):
    if not x: return None
    try:
        if isinstance(x,(int,float)):
            return dt.datetime.fromtimestamp(x/(1000 if x>1e11 else 1),dt.timezone.utc).date()
        return dt.date.fromisoformat(str(x)[:10])
    except (ValueError,OverflowError,OSError):
        return None

def trdate(x):
    return f"{x.day} {MONTHS[x.month-1]}"

def apply_updates(base, previous, incoming, *, today=None, min_coverage=0.85):
    """Tüm kontroller geçmeden HTML oluşturulmuş olsa bile yayınlanabilir bayrak verilmez."""
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date()
    old_fl,_,_ = block(base,"FL")
    if len(old_fl["funds"])<2000 or len(old_fl["rows"])<10000:
        raise ValueError("Özgün fon / portföy listesi bütünlüğü bozulmuş")
    fl=copy.deepcopy(old_fl)
    lookup={f[0].upper():i for i,f in enumerate(fl["funds"])}
    if len(lookup)!=len(fl["funds"]): raise ValueError("Çakışan fon kodları")
    accepted=copy.deepcopy(previous or {})
    rejected=Counter()
    seen=set()
    valid_dates=[]
    accepted_count=0
    found=0
    report={"date":today.isoformat(),"source_sha256":hashlib.sha256(base.encode("utf-8")).hexdigest(),
            "source_rows":len(incoming),"fund_count":len(lookup),"publish":False}
    for row in incoming:
        code=str(row.get("code") or "").strip().upper()
        if code not in lookup: continue
        if code in seen:
            rejected["duplicate"]+=1
            continue
        seen.add(code)
        raw=fl["funds"][lookup[code]]
        prev=accepted.get(code) or {}
        old_aum=numeric(prev.get("aum")) if prev.get("aum") is not None else numeric(raw[6])
        dt_new=day(row.get("current_date"))
        dt_old=day(prev.get("current_date")) or BASE_DATE
        price=numeric(row.get("current_price"))
        aum=numeric(row.get("aum"))
        investors=numeric(row.get("investor_count"))
        if not dt_new or dt_new<BASE_DATE or dt_new>today+dt.timedelta(days=1) or dt_new<dt_old:
            rejected["invalid_date"]+=1
            continue
        if price is None or price<=0 or aum is None or aum<0 or investors is None or investors<0 or not investors.is_integer():
            rejected["invalid_numeric"]+=1
            continue
        if old_aum is None or old_aum<=0:
            rejected["missing_baseline"]+=1
            continue
        if abs(aum/old_aum-1)>0.5:
            rejected["large_aum_change"]+=1
            continue
        found+=1
        valid_dates.append(dt_new)
        value={"code":code,"current_date":dt_new.isoformat(),"current_price":price,
               "aum":aum,"investor_count":int(investors),"source":"Fonoloji/TEFAS"}
        if accepted.get(code)!=value:
            accepted[code]=value
            accepted_count+=1
    coverage=found/len(lookup)
    report.update({"found":found,"coverage":round(coverage,4),"accepted_new":accepted_count,"rejected":dict(rejected)})
    if coverage<min_coverage or not valid_dates:
        report["reason"]="Yetersiz doğrulanmış veri kapsamı"
        return base,previous,report
    dominant,qty=Counter(valid_dates).most_common(1)[0]
    report.update({"dominant_date":dominant.isoformat(),"dominant_date_share":round(qty/found,4)})
    if qty/found<0.80:
        report["reason"]="Fiyat tarihleri birbirinden çok farklı"
        return base,previous,report
    for f in fl["funds"]:
        data=accepted.get(f[0])
        if data:
            f[5]=data["investor_count"]
            f[6]=data["aum"]
    for r in fl["rows"]:
        idx=r[0]
        old_size=old_fl["funds"][idx][6]
        new_size=fl["funds"][idx][6]
        if old_size and old_size>0 and new_size!=old_size:
            r[4]=round(r[4]*new_size/old_size,2)
    out=patch(base,"FL",fl)
    # Yalnızca mevcut rapor tarihini gösteren sabit 5 Kasım etiketleri yenilenir.
    out=out.replace("5 Kasım",trdate(dominant))
    settings,_,_=block(out,"AYAR")
    settings["vgun"]=trdate(dominant)
    out=patch(out,"AYAR",settings)
    for name in ("R","KAL","RA","RAFD","LOGOS"):
        if block(out,name)[0]!=block(base,name)[0]:
            raise ValueError("Korunan veri bloğu değişmiş: "+name)
    base_settings=block(base,"AYAR")[0]
    if {k:v for k,v in block(out,"AYAR")[0].items() if k!="vgun"} != {k:v for k,v in base_settings.items() if k!="vgun"}:
        raise ValueError("Ayar alanları beklenmedik biçimde değişmiş")
    check=block(out,"FL")[0]
    if len(check["funds"])!=len(old_fl["funds"]) or len(check["rows"])!=len(old_fl["rows"]):
        raise ValueError("Kayıt sayıları bozuldu")
    totals=defaultdict(float)
    for row in check["rows"]: totals[row[0]]+=row[4]
    inconsistent=[f[0] for i,f in enumerate(check["funds"]) if i in totals and abs(totals[i]-f[6])>max(10,abs(f[6])*0.001)]
    if inconsistent:
        report["reason"]="Fon büyüklüğü ile pozisyon toplamı uyuşmuyor"
        report["examples"]=inconsistent[:20]
        return base,previous,report
    report["publish"]=True
    report["reason"]="Doğrulandı"
    return out,accepted,report
