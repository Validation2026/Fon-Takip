"""One-off safe schema probe for the Fonoloji KAP/portfolio REST responses."""
import json
import os
import sys
from update_rolling import api_get

def shape(obj,depth=0):
    if isinstance(obj,list):
        return {"type":"list","count":len(obj),"sample_shape":shape(obj[0],depth+1) if obj and depth<3 else None}
    if isinstance(obj,dict):
        result={"type":"object","keys":list(obj)}
        if depth<3:
            result["children"]={k:shape(v,depth+1) for k,v in obj.items() if isinstance(v,(list,dict))}
        return result
    return {"type":type(obj).__name__}

def main():
    key=os.environ.get("FONOLOJI_KEY")
    if not key:raise RuntimeError("API key missing")
    for name,route in [
        ("portfolio","/funds/TLY/portfolio?include=allocation,holdings,dates"),
        ("disclosures","/funds/TLY/analysis?include=disclosures"),
    ]:
        data=api_get(route,key)
        print("KAP_SCHEMA",name,json.dumps(shape(data),ensure_ascii=False),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as ex:
        print("KAP_SCHEMA_ERROR",type(ex).__name__,str(ex)[:200],file=sys.stderr,flush=True)
        raise
