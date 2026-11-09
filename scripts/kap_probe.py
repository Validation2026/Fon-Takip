"""Read-only KAP field schema probe. Never logs full records, auth keys or money amounts."""
import json
import os
import sys
import urllib.error
import urllib.request

def shape(obj,depth=0):
    if isinstance(obj,list):
        return {"type":"list","count":len(obj),"sample_shape":shape(obj[0],depth+1) if obj and depth<3 else None}
    if isinstance(obj,dict):
        out={"type":"object","keys":list(obj)}
        if depth<3:
            out["children"]={k:shape(v,depth+1) for k,v in obj.items() if isinstance(v,(list,dict))}
        return out
    return {"type":type(obj).__name__}

def probe(name,path,key):
    req=urllib.request.Request("https://fonoloji.com/v1"+path,headers={
        "X-API-Key":key,"Accept":"application/json","User-Agent":"FonTakipDashboard/2.0"})
    try:
        with urllib.request.urlopen(req,timeout=22) as r:
            data=r.read(6_000_001)
            print("KAP_PROBE_META",json.dumps({
                "endpoint":name,"status":r.status,"mime":r.headers.get('Content-Type'),
                "byte_count":len(data),"over_6mb":len(data)>6_000_000,
                "looks_html":data[:100].lstrip().startswith(b'<')
            }),flush=True)
        if len(data)>6_000_000: return
        try:
            parsed=json.loads(data)
            print("KAP_SCHEMA",name,json.dumps(shape(parsed),ensure_ascii=False),flush=True)
        except (ValueError,UnicodeError) as exc:
            print("KAP_PROBE_PARSE_FAILURE",name,type(exc).__name__,flush=True)
    except urllib.error.HTTPError as exc:
        print("KAP_PROBE_HTTP",name,exc.code,flush=True)
    except Exception as exc:
        print("KAP_PROBE_ERROR",name,type(exc).__name__,flush=True)

def main():
    key=os.environ.get("FONOLOJI_KEY","")
    if len(key)<8:
        print("KAP_PROBE_SKIP no API key",flush=True)
        return
    probe("portfolio","/funds/TLY/portfolio?include=allocation,holdings,dates",key)
    probe("disclosures","/funds/TLY/analysis?include=disclosures",key)

if __name__=="__main__":main()
