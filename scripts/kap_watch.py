"""Read-only KAP reference audit sourced from Fonoloji.

No payment status is inferred, no holding weight is applied, and existing
dashboard blocks remain unchanged. This writes only audit/kap_latest.json.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
AUDIT=ROOT/'audit'/'kap_latest.json'
BASE='https://fonoloji.com/v1'
TZ=dt.timezone(dt.timedelta(hours=3))
CODES=('TLY','TP2')
MAX_BYTES=4_000_000

def get(path,key):
    req=urllib.request.Request(BASE+path,headers={
        'X-API-Key':key,'Accept':'application/json',
        'User-Agent':'FonTakipDashboard/2.0'})
    try:
        with urllib.request.urlopen(req,timeout=35) as response:
            if response.status!=200:raise RuntimeError('Unexpected response status')
            body=response.read(MAX_BYTES+1)
        if len(body)>MAX_BYTES or body.lstrip().startswith(b'<'):
            raise ValueError('Unexpected KAP source size/format')
        data=json.loads(body)
        if not isinstance(data,dict):raise ValueError('KAP response is not a JSON object')
        return data
    except urllib.error.HTTPError as exc:
        raise RuntimeError('KAP source returned HTTP %d'%exc.code) from None

def watch_record(code,portfolio,analysis):
    if not re.fullmatch(r'[A-Z0-9]{2,8}',code):
        raise ValueError('Invalid watched fund code')
    if portfolio.get('code')!=code or analysis.get('code')!=code:
        raise ValueError('Fund code mismatch: '+code)
    h=portfolio.get('holdings')
    d=analysis.get('disclosures')
    if not isinstance(h,dict) or not isinstance(d,dict):
        raise ValueError('Missing holdings or disclosure block: '+code)
    if h.get('code')!=code or d.get('code')!=code:
        raise ValueError('Block code mismatch: '+code)
    holdings=h.get('items')
    disclosures=d.get('items')
    if not isinstance(holdings,list) or not isinstance(disclosures,list):
        raise ValueError('Invalid holdings/disclosures lists: '+code)
    report_period=h.get('latestPeriod')
    if not holdings or not isinstance(report_period,str) or not report_period.strip():
        raise ValueError('No dated KAP holdings report: '+code)
    indices=set()
    safe_disclosures=[]
    for item in disclosures[:25]:
        if not isinstance(item,dict):continue
        idx=item.get('disclosure_index')
        if not isinstance(idx,int) or idx<=0 or idx in indices:continue
        indices.add(idx)
        subject=str(item.get('subject') or '')[:180]
        raw_date=item.get('publish_date')
        if not isinstance(raw_date,(int,float)) or raw_date<=0:continue
        try:
            stamped=dt.datetime.fromtimestamp(raw_date/1000 if raw_date>1e11 else raw_date,dt.timezone.utc)
        except (OSError,OverflowError,ValueError):
            continue
        if stamped.year<2010 or stamped>dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1):
            continue
        safe_disclosures.append({
            'index':idx,'published_at':stamped.isoformat(timespec='seconds'),
            'subject':subject,
            'kap_url':'https://www.kap.org.tr/tr/Bildirim/'+str(idx),
        })
    return {
        'code':code,
        'portfolio_period':report_period,
        'holdings_report_publish_date':h.get('latestPublishDate'),
        'holdings_record_count':len(holdings),
        'latest_disclosures':safe_disclosures,
        'payment_status':'NOT_VERIFIED',
        'payment_status_note':'Bildirim basligi veya AI ozeti odeme gerceklesti kaniti sayilmaz.',
        'holdings_used_in_original_dashboard':False
    }

def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(text,encoding='utf8')
    tmp.replace(path)

def main():
    key=os.environ.get('FONOLOJI_KEY','')
    if len(key)<8:raise RuntimeError('FONOLOJI_KEY missing')
    timestamp=dt.datetime.now(TZ).isoformat(timespec='seconds')
    report={'retrieved_at':timestamp,'source':'Fonoloji KAP-derived data',
        'status':'PILOT_REFERENCE_ONLY','watched_funds':list(CODES),
        'funds':[],'errors':[],
        'note':'Read-only pilot. No official KAP API subscription; no payment/portfolio fields on the original site are edited.'}
    for code in CODES:
        try:
            p=get('/funds/'+urllib.parse.quote(code)+'/portfolio?include=allocation,holdings,dates',key)
            d=get('/funds/'+urllib.parse.quote(code)+'/analysis?include=disclosures',key)
            report['funds'].append(watch_record(code,p,d))
        except Exception as exc:
            report['errors'].append({'code':code,'type':type(exc).__name__,'reason':str(exc)[:180]})
    report['status']='PILOT_VERIFIED' if len(report['funds'])==len(CODES) else 'PILOT_INCOMPLETE'
    save_json(AUDIT,report)
    print('KAP_AUDIT',json.dumps({
        'status':report['status'],'retrieved_at':timestamp,
        'valid_funds':len(report['funds']),
        'holdings_counts':{f['code']:f['holdings_record_count'] for f in report['funds']},
        'disclosures_counts':{f['code']:len(f['latest_disclosures']) for f in report['funds']},
        'errors':report['errors'],
    },ensure_ascii=False),flush=True)
    if report['status']!='PILOT_VERIFIED':
        raise RuntimeError('At least one pilot fund failed KAP validation')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('KAP audit did not pass:',type(exc).__name__,str(exc)[:200],file=sys.stderr)
        raise SystemExit(1)
