"""Quota-aware rolling Fonoloji refresh. Never asserts an identical NAV date for all funds."""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from bootstrap import build
from fon_core import BASE_DATE, block, day, numeric, patch

ROOT=Path(__file__).resolve().parent.parent
STATE=ROOT/'state'/'funds.json'
SCAN=ROOT/'state'/'scan.json'
PUBLIC=ROOT/'public'/'index.html'
PRICES=ROOT/'public'/'data'/'fund_prices.json'
AUDIT=ROOT/'audit'/'latest.json'
API='https://fonoloji.com/v1'
TZ=dt.timezone(dt.timedelta(hours=3))
BATCH_LIMIT=int(os.environ.get('FONOLOJI_BATCH_LIMIT','400'))
MAX_AGE_DAYS=10

def read_json(path):
    return json.loads(path.read_text('utf8')) if path.exists() else {}

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    tmp.replace(path)

def api_get(path,key):
    req=urllib.request.Request(API+path,headers={
        'X-API-Key':key,'User-Agent':'FonTakipDashboard/2.0','Accept':'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=25) as response:
                if response.status!=200:raise RuntimeError('Unexpected HTTP status')
                raw=response.read(1_000_001)
                if len(raw)>1_000_000 or raw.lstrip().startswith(b'<'):
                    raise ValueError('Invalid API response')
                data=json.loads(raw)
                if not isinstance(data,dict):raise ValueError('Unexpected JSON shape')
                return data
        except urllib.error.HTTPError as exc:
            if exc.code==404:return None
            if exc.code in (401,403):raise RuntimeError('Fonoloji API authorization denied')
            if exc.code in (429,500,502,503,504) and attempt<2:
                retry=exc.headers.get('Retry-After','')
                delay=min(70,float(retry)) if retry.replace('.','',1).isdigit() else 3*(attempt+1)
                time.sleep(delay)
                continue
            raise RuntimeError('Fonoloji HTTP %d'%exc.code)
        except (urllib.error.URLError,TimeoutError,OSError) as exc:
            if attempt==2:raise RuntimeError('Fonoloji connection failed: '+type(exc).__name__)
            time.sleep(3*(attempt+1))
    raise RuntimeError('Fonoloji retries exhausted')

def budget(remaining,ceiling=BATCH_LIMIT):
    if not isinstance(remaining,dict):raise ValueError('Missing quota')
    daily,monthly=remaining.get('today'),remaining.get('this_month')
    if not isinstance(daily,int) or not isinstance(monthly,int):
        raise ValueError('Invalid quota numbers')
    return max(0,min(ceiling,daily-30,monthly-100))

def normalize_fund(data,code):
    fund=data.get('fund') if data else None
    if not isinstance(fund,dict):return None
    if str(fund.get('code') or '').upper()!=code:
        raise ValueError('Wrong code in Fonoloji response')
    return {k:fund.get(k) for k in ('code','current_date','current_price','aum','investor_count')}

def validate(row,prior,reference_aum,today):
    code=row['code']
    price=numeric(row.get('current_price'))
    size=numeric(row.get('aum'))
    investors=numeric(row.get('investor_count'))
    new_date=day(row.get('current_date'))
    old_date=day(prior.get('current_date')) or BASE_DATE
    old_aum=numeric(prior.get('aum')) if prior.get('aum') is not None else numeric(reference_aum)
    if not new_date or new_date<BASE_DATE or new_date>today+dt.timedelta(days=1) or new_date<old_date:
        return None,'invalid_date'
    if price is None or price<=0 or size is None or size<0 or investors is None or investors<0 or not investors.is_integer():
        return None,'invalid_numeric'
    if old_aum is None or old_aum<=0:return None,'missing_baseline'
    if abs(size/old_aum-1)>.5:return None,'large_aum_change'
    return {'code':code,'current_date':new_date.isoformat(),'current_price':price,
            'aum':size,'investor_count':int(investors),'source':'Fonoloji/TEFAS'},None

def refreshed_html(base,updated):
    import copy
    original,_,_=block(base,'FL')
    fl=copy.deepcopy(original)
    for f in fl['funds']:
        data=updated.get(f[0])
        if data:
            f[5]=data['investor_count']
            f[6]=data['aum']
    for r in fl['rows']:
        idx=r[0]
        previous=numeric(original['funds'][idx][6])
        current=numeric(fl['funds'][idx][6])
        if previous and previous>0 and current is not None and current!=previous:
            r[4]=round(r[4]*current/previous,2)
    html=patch(base,'FL',fl)
    html=html.replace('Fon bazında güncel (5 Kasım) fon büyüklüğü ve yatırımcı sayısı.',
                      'Fon bazında son erişilebilir tarihli fon büyüklüğü ve yatırımcı sayısı. Tarihler fonlara göre farklılık gösterebilir.')
    html=html.replace('fon büyüklüğü (5 Kasım)','fon büyüklüğü (fon bazında son veri tarihi)')
    settings,_,_=block(html,'AYAR')
    settings['vgun']='Fon bazında farklı'
    html=patch(html,'AYAR',settings)
    for name in ('R','KAL','RA','RAFD','LOGOS'):
        if block(base,name)[0]!=block(html,name)[0]:
            raise ValueError('Protected KAP block changed: '+name)
    check,_,_=block(html,'FL')
    if len(check['funds'])!=len(original['funds']) or len(check['rows'])!=len(original['rows']):
        raise ValueError('Original fund/holding list damaged')
    totals=defaultdict(float)
    for row in check['rows']:totals[row[0]]+=row[4]
    bad=[f[0] for i,f in enumerate(check['funds'])
         if i in totals and abs(totals[i]-f[6])>max(10,abs(f[6])*.001)]
    if bad:raise ValueError('Holdings/size check failed: '+','.join(bad[:10]))
    return html

def run():
    key=os.environ.get('FONOLOJI_KEY','')
    if len(key)<8:raise ValueError('FONOLOJI_KEY missing')
    original=build().decode('utf8')
    fl,_,_=block(original,'FL')
    codes=[str(f[0]).upper() for f in fl['funds']]
    if len(codes)<2000 or len(codes)!=len(set(codes)) or len(fl['rows'])<10000:
        raise ValueError('Original dashboard inventory invalid')
    today=dt.datetime.now(TZ).date()
    timestamp=dt.datetime.now(TZ).isoformat(timespec='seconds')
    prior=read_json(STATE)
    scan=read_json(SCAN)
    quota=api_get('/quota',key)
    allowance=budget(quota.get('remaining') if quota else {})
    if allowance<10:
        raise RuntimeError('Fonoloji quota insufficient; old data kept')
    chosen=sorted(codes,key=lambda c:(str(scan.get(c,'')),c))[:allowance]
    lookup={f[0]:f for f in fl['funds']}
    accepted={}
    errors=Counter()
    for i,code in enumerate(chosen):
        if not re.fullmatch(r'[A-Z0-9]{2,8}',code):
            errors['invalid_code']+=1
            scan[code]=timestamp
            continue
        response=api_get('/funds/'+urllib.parse.quote(code),key)
        scan[code]=timestamp
        if response is None:
            errors['not_found']+=1
        else:
            record=normalize_fund(response,code)
            if record is None:
                errors['invalid_payload']+=1
            else:
                good,reason=validate(record,prior.get(code) or {},lookup[code][6],today)
                if reason:errors[reason]+=1
                else:accepted[code]=good
        if i!=len(chosen)-1:time.sleep(1.08)
    merged=dict(prior)
    merged.update(accepted)
    floor=today-dt.timedelta(days=MAX_AGE_DAYS)
    usable={c:v for c,v in merged.items()
            if c in lookup and day(v.get('current_date')) and
            floor<=day(v['current_date'])<=today+dt.timedelta(days=1)}
    coverage=len(usable)/len(codes)
    report={'run_at':timestamp,'source':'Fonoloji REST API','fund_count':len(codes),
            'selected':len(chosen),'accepted_this_run':len(accepted),
            'cached_recent_valid':len(usable),'coverage':round(coverage,4),
            'quota_before':quota.get('remaining'),'errors':dict(errors),
            'price_date_counts':dict(Counter(x['current_date'] for x in usable.values())),
            'publish_html':False,'min_coverage':.85,
            'notes':'Per-fund dates vary. KAP holding weights remain original; notional estimates follow new AUM.'}
    if coverage>=.85:
        html=refreshed_html(original,usable)
        PUBLIC.parent.mkdir(parents=True,exist_ok=True)
        tmp=PUBLIC.with_name(PUBLIC.name+'.tmp')
        tmp.write_text(html,encoding='utf8')
        tmp.replace(PUBLIC)
        report['publish_html']=True
    save(STATE,merged)
    save(SCAN,scan)
    save(PRICES,{'retrieved_at':timestamp,'source':'Fonoloji/TEFAS','funds':merged,
                 'coverage':round(coverage,4),'per_fund_dates':True,
                 'note':'Every fund has its own price date; partial coverage is not advertised as universal freshness.'})
    save(AUDIT,report)
    print(json.dumps(report,ensure_ascii=False,allow_nan=False),flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(run())
    except Exception as exc:
        print('Korumalı duruş:',type(exc).__name__,str(exc),file=sys.stderr,flush=True)
        raise SystemExit(1)
